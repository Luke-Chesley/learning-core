# UI Registry

Use `read_ui_spec` to fetch the full doc for any allowlisted component or widget spec before using it.
Use good judgment. Read docs only when doing so materially helps you choose or configure a component or widget well. Many requests need no doc reads. Specialized requests may justify a few.

## Top-Level Activity Components

### Presentation (no learner input)

| type | use when | avoid when | cost | path |
|------|----------|------------|------|------|
| heading | section breaks, visual grouping | single-section activities | low | `ui_components/heading.md` |
| paragraph | framing context, brief instructions | duplicating the lesson draft verbatim | low | `ui_components/paragraph.md` |
| callout | tips, warnings, safety notes | filler encouragement | low | `ui_components/callout.md` |
| image | diagrams, reference photos, maps | decorative clip-art | low | `ui_components/image.md` |
| divider | separating clear phases | between every component | low | `ui_components/divider.md` |

### Text Input

| type | use when | avoid when | evidence | cost | path |
|------|----------|------------|----------|------|------|
| short_answer | single fact, number, label, or compact response | open-ended reasoning | answer_response | low | `ui_components/short_answer.md` |
| text_response | explanation, paragraph writing, compare-and-justify work | one-word recall | answer_response | med | `ui_components/text_response.md` |
| rich_text_response | formatted writing or longer structured response | short factual recall | answer_response | med | `ui_components/rich_text_response.md` |

### Selection / Choice

| type | use when | avoid when | evidence | cost | path |
|------|----------|------------|----------|------|------|
| single_select | one clearly best answer from options | subjective preference | answer_response | low | `ui_components/single_select.md` |
| multi_select | multiple correct answers may apply | only one answer is right | answer_response | low | `ui_components/multi_select.md` |
| rating | preference, comfort, or self-rating | factual correctness | self_assessment | low | `ui_components/rating.md` |
| confidence_check | learner self-rates understanding | grading correctness | confidence_signal | low | `ui_components/confidence_check.md` |

### Structured Interaction

| type | use when | avoid when | evidence | cost | path |
|------|----------|------------|----------|------|------|
| checklist | step-by-step task completion | ordering matters | completion_marker | low | `ui_components/checklist.md` |
| ordered_sequence | correct ordering or sequencing | order does not matter | ordering_result | med | `ui_components/ordered_sequence.md` |
| matching_pairs | pairing related ideas | too many pairs to scan comfortably | matching_result | med | `ui_components/matching_pairs.md` |
| categorization | sorting items into named categories | only 2 thin items | categorization_result | med | `ui_components/categorization.md` |
| sort_into_groups | grouping into described bins | simple binary split | categorization_result | med | `ui_components/sort_into_groups.md` |
| label_map | labeling parts on a diagram or image | no image is central | answer_response | high | `ui_components/label_map.md` |
| hotspot_select | clicking regions on an image | the image is not central evidence | answer_response | high | `ui_components/hotspot_select.md` |
| build_steps | scaffolded multi-step problem solving | generic instruction delivery | answer_response | high | `ui_components/build_steps.md` |
| drag_arrange | spatial ordering or arrangement | a simpler sequence is enough | ordering_result | med | `ui_components/drag_arrange.md` |
| interactive_widget | a rich interactive surface materially improves the task | simple components already do the job | answer_response | high | `ui_components/interactive_widget.md` |

### Reflection / Self-Assessment

| type | use when | avoid when | evidence | cost | path |
|------|----------|------------|----------|------|------|
| reflection_prompt | metacognitive reflection with sub-prompts | factual assessment | reflection_response | med | `ui_components/reflection_prompt.md` |
| rubric_self_check | learner self-evaluates against criteria | teacher-only rubrics | rubric_score | med | `ui_components/rubric_self_check.md` |
| compare_and_explain | comparing two options or ideas with explanation | no clear comparison pair | answer_response | med | `ui_components/compare_and_explain.md` |
| choose_next_step | learner chooses from plausible next actions | only one path exists | completion_marker | low | `ui_components/choose_next_step.md` |

### Evidence Capture (offline / hybrid)

| type | use when | avoid when | evidence | cost | path |
|------|----------|------------|----------|------|------|
| file_upload | submitting documents, PDFs, or images | purely digital activities with native inputs | file_artifact | low | `ui_components/file_upload.md` |
| image_capture | photographing physical work | digital-only tasks | image_artifact | low | `ui_components/image_capture.md` |
| audio_capture | verbal explanation or oral reading | text-first responses | audio_artifact | low | `ui_components/audio_capture.md` |
| observation_record | structured parent or teacher observation forms | learner-only activities | teacher_observation | med | `ui_components/observation_record.md` |
| teacher_checkoff | adult confirms demonstrated skill | no adult is present | teacher_checkoff | low | `ui_components/teacher_checkoff.md` |
| construction_space | open-ended creation or building | tightly structured recall tasks | construction_product | high | `ui_components/construction_space.md` |

## Widget Specs

These are not top-level activity components. Use them only inside `interactive_widget.widget`.

| surfaceKind | engineKind | use when | avoid when | path |
|-------------|------------|----------|------------|------|
| board_surface | chess | a board position is central evidence and the learner should inspect or play a move | the chess task is better handled as plain text or simple comparison | `ui_widgets/board_surface__chess.md` |
| expression_surface | math_symbolic | structured symbolic entry matters more than freeform text | a short answer or build_steps component is enough | `ui_widgets/expression_surface__math_symbolic.md` |
| graph_surface | graphing | graph interaction is central to the learning target | a static image, paragraph, or short answer is enough | `ui_widgets/graph_surface__graphing.md` |
| map_surface | map_geojson | the map itself is central evidence or a teaching artifact needs layers, routes, regions, or annotations | a static image, hotspot_select, or label_map is enough | `ui_widgets/map_surface__geojson.md` |
