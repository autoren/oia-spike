import numpy as np

RUNNING = "running"
LEVEL_COMPLETED = "completed"
GAME_OVER = "game_over"


def initial_state(initial_frame):
    return {"frame": np.asarray(initial_frame, dtype=np.int16).copy(), "step": 0}


def step(state, action):
    if action not in ("ACTION6", "ACTION7"):
        raise ValueError("unknown action")
    next_state = {"frame": state["frame"].copy(), "step": state["step"] + 1}
    if next_state["step"] == 1:
        next_state["frame"][63, 62:64] = 5
    elif action == "ACTION6":
        next_state["frame"][63, 60] = 5
    else:
        next_state["frame"][63, 61] = 5
    return next_state, RUNNING


def render(state):
    return state["frame"].copy()
