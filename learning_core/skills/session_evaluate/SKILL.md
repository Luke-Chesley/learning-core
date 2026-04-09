No legacy AI prompt existed for this operation in homeschool-v2.

Legacy session evaluation was deterministic and used these exact evaluation levels:

- needs_more_work: The learner did not yet show the target skill or needed significant support.
- partial: The learner showed some understanding, but the task was not fully there yet.
- successful: The learner completed the task at the expected level.
- exceeded: The learner completed the task cleanly and showed extra independence or depth.

Legacy numeric mapping:

- needs_more_work -> 1
- partial -> 2
- successful -> 3
- exceeded -> 4

If this skill is implemented as an LLM workflow later, preserve those exact rating labels and semantics from the legacy repo.
