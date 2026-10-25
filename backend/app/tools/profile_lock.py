"""One lock for the shared browser profile.

Chrome refuses to open the same user-data directory twice ("Opening in existing browser session"), so two
shopping runs at once used to make the second one fail. Runs now queue for the profile instead.
"""

import threading

PROFILE_LOCK = threading.Lock()
