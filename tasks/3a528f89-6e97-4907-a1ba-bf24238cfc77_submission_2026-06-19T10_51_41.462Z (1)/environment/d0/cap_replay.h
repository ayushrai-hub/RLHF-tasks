#ifndef CAP_REPLAY_H
#define CAP_REPLAY_H

int cap_round_replay(const char *round, const char *actor, const char *mark, const char *launch_mark, int class_tag,
                     const char *gap_code);
int cap_update_gap(const char *round, const char *actor, const char *mark, const char *gap_code);

#endif
