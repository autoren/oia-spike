from __future__ import annotations

import json
import unittest

from ontology_auditor import (
    CandidateSystem,
    CertificateValidationError,
    DecisionProblem,
    MealyMachine,
    ModelActionLoss,
    Transition,
    expected_policy_steps,
    initial_behavioral_classes,
    label_description,
    label_terminal,
    shortest_pairwise_separator,
    synthesize_adaptive_policy,
    synthesize_expected_value_policy,
    synthesize_preset_sequence,
    synthesize_robust_value_policy,
    synthesize_task_loss_policy,
    verify_adaptive_impossibility_certificate,
    verify_policy_witness,
    verify_serialized_adaptive_result,
)
from ontology_auditor.io import audit_payload


def static_machine(name: str, outputs: dict[str, str]) -> MealyMachine:
    return MealyMachine(
        name=name,
        initial_state="s",
        transitions={
            "s": {
                action: Transition(output=output, next_state="s")
                for action, output in outputs.items()
            }
        },
    )


def decision_region_system() -> CandidateSystem:
    # No one action identifies all three candidates:
    #   a: H1/H2 together, H3 separate
    #   b: H1 separate, H2/H3 together
    return CandidateSystem(
        [
            static_machine("H1", {"a": "0", "b": "0"}),
            static_machine("H2", {"a": "0", "b": "1"}),
            static_machine("H3", {"a": "1", "b": "1"}),
        ]
    )


class BehavioralAuditTests(unittest.TestCase):
    def test_direct_pairwise_separator(self) -> None:
        system = CandidateSystem(
            [
                static_machine("switch_A", {"open_A": "off", "open_B": "on"}),
                static_machine("switch_B", {"open_A": "on", "open_B": "off"}),
            ]
        )
        result = shortest_pairwise_separator(system, "switch_A", "switch_B")
        self.assertTrue(result.distinguishable)
        self.assertEqual(len(result.sequence or ()), 1)

    def test_delayed_pairwise_separator_is_shortest(self) -> None:
        left = MealyMachine(
            "left",
            "s0",
            {
                "s0": {
                    "inspect": Transition("neutral", "s0"),
                    "prime": Transition("ok", "s1"),
                },
                "s1": {
                    "inspect": Transition("red", "s1"),
                    "prime": Transition("ok", "s1"),
                },
            },
        )
        right = MealyMachine(
            "right",
            "s0",
            {
                "s0": {
                    "inspect": Transition("neutral", "s0"),
                    "prime": Transition("ok", "s1"),
                },
                "s1": {
                    "inspect": Transition("blue", "s1"),
                    "prime": Transition("ok", "s1"),
                },
            },
        )
        system = CandidateSystem([left, right])
        result = shortest_pairwise_separator(system, "left", "right")
        self.assertEqual(result.sequence, ("prime", "inspect"))

    def test_aliases_are_exactly_behaviorally_equivalent(self) -> None:
        system = CandidateSystem(
            [
                static_machine("P7", {"probe": "same"}),
                static_machine("Q9", {"probe": "same"}),
            ]
        )
        self.assertEqual(initial_behavioral_classes(system), (("P7", "Q9"),))
        pair = shortest_pairwise_separator(system, "P7", "Q9")
        self.assertFalse(pair.distinguishable)
        adaptive = synthesize_adaptive_policy(system)
        preset = synthesize_preset_sequence(system)
        self.assertEqual(adaptive.status, "impossible")
        self.assertTrue(adaptive.exact)
        self.assertIsNotNone(adaptive.impossibility_certificate)
        verify_adaptive_impossibility_certificate(
            system, adaptive.impossibility_certificate
        )
        self.assertEqual(preset.status, "impossible")
        self.assertTrue(preset.exact)

    def test_adaptive_identity_and_preset_identity(self) -> None:
        system = decision_region_system()
        adaptive = synthesize_adaptive_policy(system)
        preset = synthesize_preset_sequence(system)
        self.assertEqual(adaptive.status, "solved")
        self.assertEqual(adaptive.worst_case_steps, 2)
        self.assertIsNotNone(adaptive.policy)
        self.assertEqual(verify_policy_witness(system, adaptive.policy), 2)
        self.assertAlmostEqual(
            expected_policy_steps(system, adaptive.policy), 5.0 / 3.0
        )
        self.assertEqual(preset.sequence, ("a", "b"))

    def test_target_class_needs_less_than_full_identity(self) -> None:
        system = decision_region_system()
        labels = {"H1": "repair_A", "H2": "repair_A", "H3": "repair_B"}
        target = synthesize_adaptive_policy(
            system,
            terminal=label_terminal(labels),
            describe_leaf=label_description(labels),
        )
        identity = synthesize_adaptive_policy(system)
        self.assertEqual(target.worst_case_steps, 1)
        self.assertEqual(target.policy.action, "a")
        self.assertEqual(
            verify_policy_witness(system, target.policy, label_terminal(labels)),
            1,
        )
        self.assertEqual(identity.worst_case_steps, 2)

    def test_label_cut_across_alias_class_is_impossible(self) -> None:
        system = CandidateSystem(
            [
                static_machine("same_1", {"probe": "x"}),
                static_machine("same_2", {"probe": "x"}),
            ]
        )
        labels = {"same_1": "feature_absent", "same_2": "feature_present"}
        result = synthesize_adaptive_policy(
            system,
            terminal=label_terminal(labels),
            describe_leaf=label_description(labels),
        )
        self.assertEqual(result.status, "impossible")
        self.assertTrue(result.exact)
        self.assertIsNotNone(result.impossibility_certificate)
        verify_adaptive_impossibility_certificate(
            system,
            result.impossibility_certificate,
            label_terminal(labels),
        )

    def test_adaptive_and_preset_caps_fail_closed(self) -> None:
        system = decision_region_system()
        adaptive = synthesize_adaptive_policy(system, max_beliefs=1)
        preset = synthesize_preset_sequence(system, max_partitions=1)
        self.assertEqual(adaptive.status, "unknown")
        self.assertFalse(adaptive.exact)
        self.assertIsNone(adaptive.policy)
        self.assertIsNone(adaptive.impossibility_certificate)
        self.assertEqual(preset.status, "unknown")
        self.assertFalse(preset.exact)
        self.assertIsNone(preset.sequence)

    def test_cap_limited_policy_is_witness_not_minimum_claim(self) -> None:
        left = MealyMachine(
            "left",
            "s0",
            {
                "s0": {
                    "a": Transition("0", "s0"),
                    "b": Transition("same", "s1"),
                },
                "s1": {
                    "a": Transition("0", "s1"),
                    "b": Transition("same", "s1"),
                },
            },
        )
        right = MealyMachine(
            "right",
            "s0",
            {
                "s0": {
                    "a": Transition("1", "s0"),
                    "b": Transition("same", "s1"),
                },
                "s1": {
                    "a": Transition("1", "s1"),
                    "b": Transition("same", "s1"),
                },
            },
        )
        system = CandidateSystem([left, right])
        result = synthesize_adaptive_policy(system, max_beliefs=3)
        self.assertEqual(result.status, "witness")
        self.assertFalse(result.exact)
        self.assertFalse(result.enumeration_complete)
        self.assertFalse(result.optimality_certified)
        self.assertEqual(result.depth_claim, "witness_upper_bound")
        self.assertEqual(result.worst_case_steps, 1)
        self.assertIsNotNone(result.policy)
        self.assertIsNone(result.impossibility_certificate)
        self.assertEqual(verify_policy_witness(system, result.policy), 1)
        self.assertEqual(
            verify_serialized_adaptive_result(
                system, json.loads(json.dumps(result.to_dict()))
            ),
            1,
        )

    def test_cap_limited_run_never_reports_impossibility(self) -> None:
        machines = []
        for name in ("same_1", "same_2"):
            machines.append(
                MealyMachine(
                    name,
                    "s0",
                    {
                        "s0": {
                            "a": Transition("x", "s1"),
                            "b": Transition("x", "s0"),
                        },
                        "s1": {
                            "a": Transition("x", "s1"),
                            "b": Transition("x", "s1"),
                        },
                    },
                )
            )
        system = CandidateSystem(machines)
        result = synthesize_adaptive_policy(system, max_beliefs=1)
        self.assertEqual(result.status, "unknown")
        self.assertFalse(result.exact)
        self.assertFalse(result.enumeration_complete)
        self.assertIsNone(result.impossibility_certificate)


class DecisionValueTests(unittest.TestCase):
    def setUp(self) -> None:
        self.system = decision_region_system()
        self.problem = DecisionProblem(
            decisions=("repair_A", "repair_B"),
            utilities={
                "H1": {"repair_A": 10.0, "repair_B": 0.0},
                "H2": {"repair_A": 10.0, "repair_B": 0.0},
                "H3": {"repair_A": 0.0, "repair_B": 10.0},
            },
        )

    def test_low_cost_probe_has_positive_expected_value(self) -> None:
        result = synthesize_expected_value_policy(
            self.system,
            self.problem,
            action_costs={"a": 1.0, "b": 1.0},
            max_depth=2,
        )
        self.assertAlmostEqual(result.baseline_value, 20.0 / 3.0)
        self.assertAlmostEqual(result.value, 9.0)
        self.assertGreater(result.value_of_information, 0.0)
        self.assertEqual(result.policy.action, "a")

    def test_high_cost_probe_is_rejected(self) -> None:
        result = synthesize_expected_value_policy(
            self.system,
            self.problem,
            action_costs={"a": 4.0, "b": 4.0},
            max_depth=2,
        )
        self.assertAlmostEqual(result.value, 20.0 / 3.0)
        self.assertTrue(result.policy.is_leaf)
        self.assertEqual(result.policy.decision, "repair_A")

    def test_low_cost_probe_has_positive_robust_value(self) -> None:
        result = synthesize_robust_value_policy(
            self.system,
            self.problem,
            action_costs={"a": 1.0, "b": 1.0},
            max_depth=2,
        )
        self.assertEqual(result.baseline_value, 0.0)
        self.assertEqual(result.value, 9.0)
        self.assertEqual(result.policy.action, "a")

    def test_uniform_task_loss_matches_scalar_cost_result(self) -> None:
        losses = ModelActionLoss(
            {
                model: {"a": 1.0, "b": 1.0}
                for model in self.system.machines
            }
        )
        expected = synthesize_task_loss_policy(
            self.system,
            self.problem,
            losses,
            criterion="expected",
            max_depth=2,
        )
        robust = synthesize_task_loss_policy(
            self.system,
            self.problem,
            losses,
            criterion="robust",
            max_depth=2,
        )
        self.assertTrue(expected.exact)
        self.assertAlmostEqual(expected.value or 0.0, 9.0)
        self.assertEqual(expected.policy.action, "a")
        self.assertTrue(robust.exact)
        self.assertAlmostEqual(robust.value or 0.0, 9.0)
        self.assertEqual(robust.policy.action, "a")

    def test_expected_and_robust_can_choose_different_task_loss_profiles(self) -> None:
        # Both probes reveal the true model immediately. The rare candidate
        # makes probe b cheaper in expectation but worse in the worst case.
        system = CandidateSystem(
            [
                static_machine("H0", {"a": "0", "b": "0"}),
                static_machine("H1", {"a": "1", "b": "1"}),
            ]
        )
        problem = DecisionProblem(
            decisions=("choose_0", "choose_1"),
            utilities={
                "H0": {"choose_0": 10.0, "choose_1": 0.0},
                "H1": {"choose_0": 0.0, "choose_1": 10.0},
            },
        )
        losses = ModelActionLoss(
            {
                "H0": {"a": 0.5, "b": 0.01},
                "H1": {"a": 0.5, "b": 1.0},
            }
        )
        expected = synthesize_task_loss_policy(
            system,
            problem,
            losses,
            criterion="expected",
            priors={"H0": 0.9, "H1": 0.1},
            max_depth=1,
        )
        robust = synthesize_task_loss_policy(
            system,
            problem,
            losses,
            criterion="robust",
            max_depth=1,
        )
        self.assertAlmostEqual(expected.value or 0.0, 9.891)
        self.assertEqual(expected.policy.action, "b")
        self.assertAlmostEqual(robust.value or 0.0, 9.5)
        self.assertEqual(robust.policy.action, "a")

    def test_task_loss_policy_rejects_destructive_probe(self) -> None:
        losses = ModelActionLoss(
            {
                model: {"a": 20.0, "b": 20.0}
                for model in self.system.machines
            }
        )
        result = synthesize_task_loss_policy(
            self.system,
            self.problem,
            losses,
            criterion="expected",
            max_depth=2,
        )
        self.assertAlmostEqual(result.value or 0.0, 20.0 / 3.0)
        self.assertTrue(result.policy.is_leaf)
        self.assertEqual(result.policy.decision, "repair_A")

    def test_task_loss_frontier_cap_fails_closed(self) -> None:
        losses = ModelActionLoss(
            {
                model: {"a": 1.0, "b": 1.0}
                for model in self.system.machines
            }
        )
        result = synthesize_task_loss_policy(
            self.system,
            self.problem,
            losses,
            criterion="expected",
            max_depth=0,
            max_frontier=1,
        )
        self.assertEqual(result.status, "unknown")
        self.assertFalse(result.exact)
        self.assertIsNone(result.value)
        self.assertIsNone(result.policy)


class JsonInterfaceTests(unittest.TestCase):
    def test_end_to_end_payload(self) -> None:
        payload = {
            "machines": [machine.to_dict() for machine in decision_region_system().machines.values()],
            "labels": {"H1": "A", "H2": "A", "H3": "B"},
            "decision_problem": {
                "decisions": ["repair_A", "repair_B"],
                "utilities": {
                    "H1": {"repair_A": 10, "repair_B": 0},
                    "H2": {"repair_A": 10, "repair_B": 0},
                    "H3": {"repair_A": 0, "repair_B": 10},
                },
            },
            "action_costs": {"a": 1, "b": 1},
            "task_losses": {
                "H1": {"a": 1, "b": 1},
                "H2": {"a": 1, "b": 1},
                "H3": {"a": 1, "b": 1},
            },
            "options": {"value_depth": 2},
        }
        report = audit_payload(json.loads(json.dumps(payload)))
        system = decision_region_system()
        self.assertEqual(
            report["target_class_identification"]["adaptive"]["worst_case_steps"],
            1,
        )
        self.assertEqual(
            report["full_candidate_identification"]["adaptive"]["worst_case_steps"],
            2,
        )
        self.assertAlmostEqual(
            report["decision_relevance"]["expected_value_policy"]["value"],
            9.0,
        )
        self.assertAlmostEqual(
            report["decision_relevance"]["model_dependent_task_loss"]
            ["expected_value_policy"]["value"],
            9.0,
        )
        self.assertEqual(
            verify_serialized_adaptive_result(
                system,
                report["full_candidate_identification"]["adaptive"],
            ),
            2,
        )
        self.assertEqual(
            verify_serialized_adaptive_result(
                system,
                report["target_class_identification"]["adaptive"],
                label_terminal(payload["labels"]),
            ),
            1,
        )

    def test_serialized_impossibility_certificate_round_trip(self) -> None:
        system = CandidateSystem(
            [
                static_machine("same_1", {"probe": "x"}),
                static_machine("same_2", {"probe": "x"}),
            ]
        )
        labels = {"same_1": "absent", "same_2": "present"}
        result = synthesize_adaptive_policy(
            system,
            terminal=label_terminal(labels),
            describe_leaf=label_description(labels),
        )
        serialized = json.loads(json.dumps(result.to_dict()))
        self.assertIsNone(
            verify_serialized_adaptive_result(
                system,
                serialized,
                label_terminal(labels),
            )
        )

    def test_serialized_policy_tampering_is_rejected(self) -> None:
        system = decision_region_system()
        result = synthesize_adaptive_policy(system)
        serialized = json.loads(json.dumps(result.to_dict()))
        root_branches = serialized["policy"]["branches"]
        root_branches.pop(next(iter(root_branches)))
        with self.assertRaises(CertificateValidationError):
            verify_serialized_adaptive_result(system, serialized)

    def test_serialized_witness_cannot_claim_exact_optimality(self) -> None:
        left = MealyMachine(
            "left",
            "s0",
            {
                "s0": {"a": Transition("0", "s0"), "b": Transition("x", "s1")},
                "s1": {"a": Transition("0", "s1"), "b": Transition("x", "s1")},
            },
        )
        right = MealyMachine(
            "right",
            "s0",
            {
                "s0": {"a": Transition("1", "s0"), "b": Transition("x", "s1")},
                "s1": {"a": Transition("1", "s1"), "b": Transition("x", "s1")},
            },
        )
        system = CandidateSystem([left, right])
        serialized = synthesize_adaptive_policy(system, max_beliefs=3).to_dict()
        serialized["status"] = "solved"
        serialized["exact"] = True
        serialized["enumeration_complete"] = False
        serialized["optimality_certified"] = True
        serialized["depth_claim"] = "minimum"
        with self.assertRaises(CertificateValidationError):
            verify_serialized_adaptive_result(system, serialized)

    def test_serialized_certificate_tampering_is_rejected(self) -> None:
        system = CandidateSystem(
            [
                static_machine("same_1", {"probe": "x"}),
                static_machine("same_2", {"probe": "x"}),
            ]
        )
        labels = {"same_1": "absent", "same_2": "present"}
        result = synthesize_adaptive_policy(
            system,
            terminal=label_terminal(labels),
            describe_leaf=label_description(labels),
        )
        serialized = json.loads(json.dumps(result.to_dict()))
        serialized["impossibility_certificate"]["blocking_successors"].clear()
        with self.assertRaises(CertificateValidationError):
            verify_serialized_adaptive_result(
                system,
                serialized,
                label_terminal(labels),
            )


if __name__ == "__main__":
    unittest.main()
