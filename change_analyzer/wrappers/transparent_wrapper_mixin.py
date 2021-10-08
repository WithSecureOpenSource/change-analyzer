from typing import Any


class TransparentWrapperMixin:
    def __getattribute__(self, name) -> Any:
        # TODO refactor as this extremely dirty hack will work only if AppEnv is the very previous to SequenceRecorder
        # or all the previous wrappers has this mixin
        if name == "action_space":
            return self.env.action_space
        if name == "observation_space":
            return self.env.observation_space

        return object.__getattribute__(self, name)
