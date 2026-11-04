# Licensing review (not legal advice)

Question: is it appropriate to add an MIT license to this repository? **No license has been added.** This page records what I checked so you can decide.

## What I verified

1. **Third-party dependencies are compatible with MIT.** Every runtime dependency (Python and npm) is under a permissive license: MIT, BSD-3-Clause, Apache-2.0, ISC, PSF-2.0. Two Python packages (`certifi`, `tqdm`) are MPL-2.0, which only requires sharing changes to those files if you modify them; we do not. See [../THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md).
2. **Bundled fonts** (Inter, JetBrains Mono) are SIL OFL 1.1. This allows bundling with software, and requires keeping the copyright and license notice, which is now in `THIRD_PARTY_NOTICES.md`.
3. **Instructor material is not in this repository.** I checked that `ASSIGNMENT_REQUIREMENTS.md` and the assignment's grading text were not copied. What came from the assignment is your own implementation: the reviewer prompts, agent loop, tool code and diff parser.
4. **The assignment files I read contain no license, copyright or sharing restriction.** They only ask for a GitHub link (with the professor as collaborator) and an AI-tools disclosure.

## What I could not verify

- **Seneca's rules about publishing coursework.** The syllabus for AIP444 and the college's academic-integrity and intellectual-property policies are not in the files I can see. Some courses forbid posting assignment solutions publicly, especially while the assignment is reused for later cohorts. **Check the syllabus or ask your professor before making the repo public**, and mention that the project started as AIP444 coursework (the README already says so).
- **Authorship and AI-generated code.** Much of this repository was written with an AI coding assistant. Copyright in AI-generated material is unsettled; you can still license what you are entitled to license, but it is another reason to be honest about how the project was built (see the co-op readiness checklist).
- **Whether the assignment's AI-use disclosure or academic rules apply** to a derived portfolio project. A short email to the professor settles it.

## Recommendation

- MIT is the usual, appropriate choice for a portfolio project and is compatible with all dependencies.
- Before adding it: (1) confirm the coursework question above, (2) confirm you are comfortable licensing the whole repository, and (3) put your legal name or GitHub handle in the copyright line.
- Alternative if you want to show the code but not invite reuse: no license (default copyright applies; others may view but not reuse) or a source-available license.
- When you confirm, I will add `LICENSE` (MIT, "Copyright (c) 2026 <your name>"), mention it in the README, and commit it.
