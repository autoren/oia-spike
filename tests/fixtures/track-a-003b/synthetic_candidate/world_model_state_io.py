def initial_state_reconstruction(level_index, initial_frame):
    return {"level_index": level_index, "frame": initial_frame.copy()}


def state_renderer(state):
    return state["frame"]
