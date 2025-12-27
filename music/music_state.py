

class MusicState:
    """Clase para manejar el estado de la música en un servidor específico."""
    
    def __init__(self):
        self.queue: list[dict] = []
        self.loop: bool = False
        self.volume: float = 0.5  # Volumen por defecto al 50%
        self.current: dict | None = None