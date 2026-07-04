#include "aggregate/demand_track.h"

void demand_track_reset(DemandTrack *track) {
    track->running_sum = 0.0;
    track->sample_count = 0;
}

void demand_track_note(DemandTrack *track, double interval_kw) {
    track->running_sum += interval_kw;
    track->sample_count += 1;
}

double demand_track_finalize(const DemandTrack *track) {
    if (track->sample_count <= 0) {
        return 0.0;
    }
    return track->running_sum / (double)track->sample_count;
}
