import numpy as np

RUNNING = "running"
LEVEL_COMPLETED = "level_completed"
GAME_OVER = "game_over"


def initial_state(initial_frame):
    return {"frame": np.asarray(initial_frame).copy(), "x": 0}


def step(state, action):
    result = {"frame": state["frame"].copy(), "x": state["x"]}
    result["x"] = (result["x"] + (1 if action == "ACTION6" else 2)) % 64
    result["frame"][0, :] = 0
    result["frame"][0, result["x"]] = 1
    return result, RUNNING


def render(state):
    return state["frame"].copy()
