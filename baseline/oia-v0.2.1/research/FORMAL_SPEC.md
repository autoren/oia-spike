# Formal Specification

## OIA-1 exact finite intervention-identifiability audit

## 1. Candidate semantics

Let the candidate set be

\[
\mathcal M = \{M_1,\ldots,M_n\}.
\]

Each candidate is a deterministic complete Mealy machine

\[
M_i=(S_i,s_i^0,A,O,\delta_i,\lambda_i),
\]

where:

- \(S_i\) is a finite state set;
- \(s_i^0\in S_i\) is the initial state;
- \(A\) is the shared finite intervention alphabet;
- \(O\) is the finite set of observable outputs;
- \(\delta_i:S_i\times A\to S_i\) is the state transition function; and
- \(\lambda_i:S_i\times A\to O\) is the output function.

Candidate names and metadata are outside the behavioral semantics.

A **world** is a pair \((i,s)\) denoting candidate \(M_i\) at state \(s\). A **belief** \(B\) is a finite set containing at most one world for each candidate. The initial belief is

\[
B_0=\{(i,s_i^0):1\le i\le n\}.
\]

After action \(a\) and observed output \(o\), the deterministic belief update is

\[
T(B,a,o)=\{(i,\delta_i(s,a)):(i,s)\in B,\ \lambda_i(s,a)=o\}.
\]

Only nonempty successors are possible observation branches.

## 2. Behavioral equivalence

Two machine-state nodes \((i,s)\) and \((j,t)\) are behaviorally equivalent when every finite action word produces the same output word:

\[
(i,s)\equiv(j,t)
\iff
\forall w\in A^*,\ \lambda_i^*(s,w)=\lambda_j^*(t,w).
\]

For deterministic finite machines, this relation is the greatest stable partition satisfying, for every action \(a\):

1. equivalent nodes emit the same immediate output; and
2. their successor nodes remain in the same block.

The implementation computes this relation by monotone partition refinement.

### Proposition 1 — Pairwise separator characterization

For initial candidates \(M_i,M_j\), breadth-first search over the product-state graph returns a shortest separating word when one exists. If every reachable product state closes without an output mismatch, the candidates are equivalent under every finite action word.

**Reason.** Every product path corresponds to one common action word. Breadth-first order gives minimum word length. Closing the finite reachable product graph without a mismatch establishes the stable equivalence condition at every reachable pair.

## 3. Target identification

Let

\[
\tau:\{1,\ldots,n\}\to C
\]

be a fixed predeclared target label. Candidate identity is the special case \(\tau(i)=i\). A belief is **target-pure** when

\[
|\{\tau(i):(i,s)\in B\}|\le 1.
\]

An adaptive intervention policy is a finite rooted tree. Internal nodes select actions; outgoing edges are possible observed outputs; leaves stop with a conclusion. A policy solves target identification from belief \(B\) when every executable branch reaches a target-pure leaf.

## 4. Exact adaptive fixed point

Let \(\mathcal R\) be the finite set of beliefs reachable from \(B_0\) before stopping at a target-pure belief. Define:

\[
W_0=\{B\in\mathcal R:B\text{ is target-pure}\},
\]

and iteratively

\[
W_{k+1}=W_k\cup
\left\{
B\in\mathcal R:
\exists a\in A\ \forall o\text{ possible from }(B,a),\ T(B,a,o)\in W_k
\right\}.
\]

Because \(\mathcal R\) is finite, this sequence reaches a least fixed point \(W_*\).

### Theorem 1 — Adaptive solvability and optimal depth

A finite guaranteed target-identifying policy exists from \(B_0\) if and only if \(B_0\in W_*\). Moreover, the least \(k\) for which \(B_0\in W_k\) is the minimum achievable worst-case number of interventions.

### Proof sketch

Induct on \(k\).

- Base: \(B\in W_0\) requires no intervention.
- Forward step: if an action sends every possible output successor into \(W_k\), choose that action and then use the inductively available policies; worst-case depth is at most \(k+1\).
- Reverse step: any policy of worst-case depth \(k+1\) chooses some root action whose every executable output subtree has depth at most \(k\); by induction, every successor lies in \(W_k\), so the root lies in \(W_{k+1}\).

The implementation records the least rank and reconstructs a rank-decreasing policy tree. Rank construction iterates the finite reachable-belief set in canonical belief order. After the rank fixed point is complete, policy serialization is canonicalized independently of discovery order: at each ranked nonterminal belief, v0.2.1 chooses the lexicographically smallest action among all actions whose worst successor rank is exactly one less than the belief rank. This tie rule does not change optimal depth; it selects one reproducible representative from the set of minimum-depth policies.

## 5. Exact impossibility certificate

Let

\[
L=\mathcal R\setminus W_*.
\]

When \(B_0\in L\), the following properties hold:

1. \(B_0\in L\);
2. no belief in \(L\) is target-pure; and
3. for every \(B\in L\) and every action \(a\in A\), at least one possible output \(o\) satisfies \(T(B,a,o)\in L\).

### Theorem 2 — Closed losing-set soundness

Any finite set \(L\) satisfying the three properties above proves that no adaptive policy can guarantee target identification from \(B_0\).

### Proof sketch

At every unresolved policy node, property 3 supplies a possible output branch that remains in \(L\). Following those blocking branches yields an unresolved path of arbitrary finite length. Therefore no finite tree can force every possible branch into a target-pure leaf.

The v0.2 report serializes one blocking output for every losing-belief/action pair. `verify_adaptive_impossibility_certificate` recomputes all transitions and checks the certificate without rerunning synthesis.

## 6. Preset intervention sequences

A preset experiment selects a fixed word \(w\in A^*\) in advance. The observed output history partitions the candidate worlds. The preset target is resolved exactly when every resulting partition block is target-pure.

The implementation performs breadth-first search over partition states. A first solution is therefore shortest. Complete graph closure without a solution proves that no finite preset sequence exists.

Adaptive and preset solvability are deliberately reported separately. An adaptive tree may exist even when no preset word exists.

## 7. Decision identification

Let \(D\) be a finite terminal decision set and let

\[
u_i(d)
\]

be the utility of decision \(d\) if candidate \(i\) is true. For belief \(B\), define each candidate’s optimal decision set and their common optimum:

\[
\operatorname{Opt}_i=\arg\max_{d\in D}u_i(d),
\qquad
\operatorname{CommonOpt}(B)=\bigcap_{(i,s)\in B}\operatorname{Opt}_i.
\]

A belief is decision-terminal when `CommonOpt` is nonempty. This can require fewer probes than candidate identity because multiple candidates may support the same optimal action.

The minimum probe to a common optimum is obtained by applying Theorem 1 with decision-terminality as the target predicate.

## 8. Finite-horizon value with scalar action costs

For model-independent action cost \(c(a)\), prior \(p_i\), and depth bound \(h\), the expected-value dynamic program compares:

- stopping now with the best posterior-expected terminal decision; and
- taking action \(a\), paying \(c(a)\), then continuing separately in each output branch.

The robust dynamic program replaces posterior expectation with the worst candidate outcome. These routines are exact within the stated depth for the scalar-cost model.

## 9. Candidate-dependent task loss

Let

\[
g_i(a)\ge 0
\]

be the task loss of intervention \(a\) when candidate \(i\) is true. A policy no longer has one scalar acquisition cost; it has a complete net-outcome vector

\[
v^\pi(B)=(v_i^\pi(B))_{i\in B}.
\]

Stopping with decision \(d\) produces

\[
v_i=u_i(d).
\]

Taking action \(a\) and following child policy \(\pi_o\) after output \(o\) produces

\[
v_i=u_i^{\pi_{\lambda_i(s,a)}}(T(B,a,\lambda_i(s,a)))-g_i(a).
\]

The implementation enumerates all branch-policy combinations within the depth bound and removes outcome vectors that are componentwise dominated. The remaining Pareto frontier preserves every policy that could be optimal under a monotone criterion, including:

- Bayesian expectation \(\sum_i p_i v_i\); and
- maximin value \(\min_i v_i\).

If a frontier or branch Cartesian product exceeds `max_task_loss_frontier`, the result is `unknown`. No truncated frontier is reported as exact.

The v0.2 loss model is candidate-dependent but state-independent. State-dependent loss is a direct representational extension, not yet implemented.

## 10. Complexity

Let \(m_i=|S_i|\) and \(a=|A|\).

- Pairwise separation for \(i,j\) visits at most \(m_i m_j\) product states and examines \(a\) actions per state.
- A multi-candidate belief contains one current state or absence for each candidate, so the crude finite upper bound is

\[
\prod_{i=1}^n(m_i+1)-1.
\]

Reachable beliefs can therefore grow exponentially in candidate count.
- Preset search ranges over partitions induced by output histories and can be larger still.
- Candidate-dependent task-loss frontiers can grow exponentially in candidates, output branches, and depth.

The implementation exposes these costs rather than converting cap exhaustion into a heuristic answer.

## 11. Exactness and cap vocabulary

Adaptive synthesis separates witness soundness from global optimality:

- **`solved`:** reachable-belief enumeration completed, the policy verifies against every executable branch, and `worst_case_steps` is the globally minimum worst-case depth for the supplied finite candidate system and target. The result has `exact=true`, `enumeration_complete=true`, `optimality_certified=true`, and `depth_claim="minimum"`.
- **`witness`:** enumeration stopped at `max_beliefs`, but the explored graph already contains a rank-decreasing policy whose complete executable tree verifies. The policy is sound. Its `worst_case_steps` is only the verified witness depth, hence an upper bound on the unknown global minimum. The result has `exact=false`, `enumeration_complete=false`, `optimality_certified=false`, and `depth_claim="witness_upper_bound"`.
- **`impossible`:** complete reachable-belief enumeration places the initial belief in a verified closed losing set. Cap-limited search never returns this status.
- **`unknown`:** a cap stopped enumeration before either a complete policy witness or a complete impossibility certificate was available. It carries no policy, certificate, or depth claim.

The serialized-result verifier independently executes every policy branch or checks every blocker and rejects inconsistent status/exactness metadata. In particular, a valid cap-limited witness cannot be relabelled as an exact minimum.

Preset and candidate-dependent task-loss routines have different search structures. They return `unknown` when their partition/frontier caps interrupt completeness; they do not currently expose a non-optimal preset or value witness.

## 12. Scientific boundary and two-track use

These theorems establish properties of supplied executable candidates. They do not establish that external histories determine those candidates, that candidate labels are semantically authoritative, or that the candidate family contains the external truth.

Under **Track A**, an opened public substrate may be used to validate adapter fidelity, separator execution, decision-versus-identity efficiency, outside-model behavior, exactness, and scaling. Such a result is instrument validation.

Under **Track B**, claims of necessary ontology revision, evaluator-private identification, or decision superiority require a separately sealed protocol with untouched reserves, leakage controls, authoritative outcome/utility semantics, and strong black-box/model-free comparisons.
