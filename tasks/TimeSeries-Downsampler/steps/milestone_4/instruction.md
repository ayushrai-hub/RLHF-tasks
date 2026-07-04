# Milestone 4: Capacity-Based Subtree Eviction

In our Causal Dependency Buffer, orphans can accumulate and cause memory leaks. Instead of a simple time-based timeout, we will use a strict capacity limit paired with a complex Subtree Value eviction algorithm.

You must implement an eviction mechanism in `src/eviction.rs`.

Implement `pub fn evict_over_capacity(&mut self, max_orphans: usize) -> Vec<Event>` for `CausalBuffer`:
1. **Count Unique Orphans**: Count the number of unique `event_id`s present anywhere across all lists in the `orphans` map.
2. **Capacity Check**: If the number of unique orphans strictly exceeds `max_orphans`, you must evict.
3. **Subtree Value**: To choose who to evict, calculate the **Subtree Value** for every unique orphan in the buffer. The Subtree Value of an orphan $X$ is defined as $X$'s own `value` PLUS the sum of the `value`s of all unique orphans that recursively depend on $X$. (An orphan $Y$ depends on $X$ if $X$'s `event_id` is in $Y$'s `dependency_ids`, and this relationship is transitive).
4. **Eviction Target**: Find the orphan with the **lowest Subtree Value**. If there is a tie, break the tie by choosing the orphan with the lexicographically smallest `event_id` among those tied.
5. **Cascading Eviction**: Evict that chosen orphan. Evicting an orphan means removing it completely from the buffer AND recursively evicting its entire dependent subtree (every orphan that depended on it).
6. **Repeat**: After evicting the chosen orphan and its subtree, check the capacity again. If the number of unique orphans STILL exceeds `max_orphans`, you must recalculate all Subtree Values and evict again. Repeat until the number of unique orphans is `<= max_orphans`.
7. **Cleanup**: All evicted events' `event_id`s must be added to `deadletter_ids`. Clean up any empty `Vec`s from the `orphans` map.
8. **Return**: Return a `Vec<Event>` containing exactly one instance of each evicted event, in any order.
