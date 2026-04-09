# UI Component Registry

Use `read_ui_component` to fetch the full doc for any component before using it.
Only read docs for components you are seriously considering (typically 0-2).

## Presentation (no learner input)

| type | use when | avoid when | cost |
|------|----------|------------|------|
| heading | section breaks, visual grouping | single-section activities | low |
| paragraph | framing context, brief instructions | duplicating lesson draft verbatim | low |
| callout | tips, warnings, safety notes | filler encouragement | low |
| image | diagrams, reference photos, maps | decorative clip-art | low |
| divider | separating activity phases | between every component | low |

## Text Input

| type | use when | avoid when | evidence | cost |
|------|----------|------------|----------|------|
| short_answer | single fact / word / number recall | open-ended reflection | answer_response | low |
| text_response | multi-sentence explanation, paragraph writing | one-word answers | answer_response | med |
| rich_text_response | formatted writing, essays with structure | short factual recall | answer_response | med |

## Selection / Choice

| type | use when | avoid when | evidence | cost |
|------|----------|------------|----------|------|
| single_select | one correct answer from options | subjective preference | answer_response | low |
| multi_select | multiple correct answers possible | single correct answer | answer_response | low |
| rating | Likert-scale opinion / preference | factual correctness | self_assessment | low |
| confidence_check | learner self-rates understanding | grading correctness | confidence_signal | low |

## Structured Interaction

| type | use when | avoid when | evidence | cost |
|------|----------|------------|----------|------|
| checklist | step-by-step task completion | ordering matters | completion_marker | low |
| ordered_sequence | correct ordering / sequencing | order doesn't matter | ordering_result | med |
| matching_pairs | pairing related concepts | >8 pairs (overwhelming) | matching_result | med |
| categorization | sorting items into named categories | only 2 items | categorization_result | med |
| sort_into_groups | grouping with described categories | simple binary split | categorization_result | med |
| label_map | labeling parts on a diagram/image | no image available | answer_response | high |
| hotspot_select | clicking regions on an image | no image available | answer_response | high |
| build_steps | scaffolded multi-step problem solving | generic instruction delivery | answer_response | high |
| drag_arrange | spatial ordering / free arrangement | simple linear sequence | ordering_result | med |

## Reflection / Self-Assessment

| type | use when | avoid when | evidence | cost |
|------|----------|------------|----------|------|
| reflection_prompt | metacognitive reflection with sub-questions | factual assessment | reflection_response | med |
| rubric_self_check | learner self-evaluates against criteria | teacher-only rubrics | rubric_score | med |
| compare_and_explain | analyzing similarities/differences | no clear comparison pair | answer_response | med |
| choose_next_step | learner agency in path selection | single required path | completion_marker | low |

## Evidence Capture (offline / hybrid)

| type | use when | avoid when | evidence | cost |
|------|----------|------------|----------|------|
| file_upload | submitting documents, PDFs, images | purely digital activities | file_artifact | low |
| image_capture | photographing physical work | digital-only tasks | image_artifact | low |
| audio_capture | verbal explanations, oral reading | text-preferred responses | audio_artifact | low |
| observation_record | structured teacher/parent observation forms | learner-only activities | teacher_observation | med |
| teacher_checkoff | teacher confirms skill demonstration | no teacher present | teacher_checkoff | low |
| construction_space | open-ended building / free-form creation | structured recall tasks | construction_product | high |

## Doc paths

All docs are at `ui_components/{type}.md` — e.g., `ui_components/short_answer.md`.
