from game_status import RUNNING


def world_model_engine(state: dict, action: dict) -> tuple[dict, str]:
    return {**state, "last_action": action["name"]}, RUNNING
