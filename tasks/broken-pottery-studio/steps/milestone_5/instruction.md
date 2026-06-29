Two booking management features in /app have logic errors.

The waitlist for a class session should promote students with a higher loyalty tier ahead of those with a lower one. When students share the same tier, the one who joined first should be promoted first. Waitlist positions are reported to students starting at 1 for the next person to be promoted.

A booking becomes eligible for cancellation once it has been confirmed. Bookings in confirmed or cancellation_requested status remain cancellable; only pending bookings are excluded from cancellation.
