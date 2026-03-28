import time

class KioskState:
    IDLE = "IDLE"
    ACTIVE = "ACTIVE" # 5 fingers shown
    TARGETING = "TARGETING" # 1 finger shown

class GestureManager:
    def __init__(self):
        self.state = KioskState.IDLE
        self.target_word = None
        self.lock_time = 0
        self.last_action_time = 0

    def update_state(self, fingers_up):
        current_time = time.time()
        
        # Trigger Active Mode with 5 fingers
        if fingers_up == 5 and self.state != KioskState.ACTIVE:
            self.state = KioskState.ACTIVE
            self.last_action_time = current_time
            return "Targeting Mode Active"

        # Trigger Targeting with 1 finger (Index)
        if fingers_up == 1 and self.state == KioskState.ACTIVE:
            self.state = KioskState.TARGETING
            self.lock_time = current_time
            return "Scanning point"

        # Reset to IDLE if no hand for 5 seconds
        if fingers_up == 0 and (current_time - self.last_action_time > 5):
            self.state = KioskState.IDLE
        
        return None

    def is_locked(self):
        """Checks if we are in the 4-second highlight window"""
        return time.time() - self.lock_time < 4 if self.lock_time > 0 else False