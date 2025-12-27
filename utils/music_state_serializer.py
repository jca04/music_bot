from music.music_state import MusicState

def serializer_state(state: MusicState) -> dict:
    return {
        'queue': state.queue,
        'current': state.current,
        'volume': state.volume,
        'loop': state.loop
    }

def hydrate_state(data: dict) -> MusicState:
    state = MusicState()
    state.queue = data.get('queue', [])
    state.current = data.get('current', None)
    state.volume = data.get('volume', 0.5)
    state.loop = data.get('loop', False)
    return state