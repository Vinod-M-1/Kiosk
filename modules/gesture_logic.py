import time
from enum import Enum

class KioskState(Enum):
    IDLE = "IDLE"
    ACTIVE = "ACTIVE"
    TARGETING = "TARGETING"

class GestureManager:
    def __init__(self):
        self.state = KioskState.IDLE
        self.lock_time = 0
        self._consecutive_frames = 0
        self._last_finger_count = -1
        
    def update_state(self, fingers_up):
        # Debounce the finger input to prevent jitters
        if fingers_up == self._last_finger_count:
            self._consecutive_frames += 1
        else:
            self._consecutive_frames = 0
            self._last_finger_count = fingers_up
            
        # Only change state if finger count has been stable for 10 frames (~0.3s)
        if self._consecutive_frames >= 10:
            if fingers_up >= 4 and self.state != KioskState.ACTIVE:
                self.state = KioskState.ACTIVE
                return "Targeting Mode Active"
                
            elif fingers_up == 1 and self.state == KioskState.ACTIVE:
                self.state = KioskState.TARGETING
                
            elif fingers_up == 0 and self.state != KioskState.IDLE:
                self.state = KioskState.IDLE
                return "System Idle"
                
            # If they drop fingers down after targeting, go back to Active wait
            elif fingers_up > 1 and fingers_up < 4 and self.state == KioskState.TARGETING:
                self.state = KioskState.ACTIVE
                
        return None  # No announcement needed

    def is_locked(self):
        # 4-Second read cooldown so the words don't repeat endlessly
        if time.time() - self.lock_time < 4.0:
            return True
        return False