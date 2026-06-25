# Experiment: YouTube Live Chat Nudge Bot

Extracted scheduler rules from the bundled experiment doc:

- Trigger messages when a poll is started.
- Stop the messages when the poll has ended, but keep the message stream active for the next 60 seconds once the poll ends.
- Introduce a delay of at least 10 seconds between any two messages.
- Messages rotate through the message bank in sequence.
