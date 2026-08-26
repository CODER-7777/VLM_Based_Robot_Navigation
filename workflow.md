# UGP Workflow & Tracking

## 1. Task Tracker Rules
- **Each task is a row** in the main Task Tracker (e.g., in Notion or equivalent system).
- You must update the **Status**, **Progress / Blockers**, and confirm the **Deadline** on every task.
- If **blocked for more than a day** -> write it in *Progress / Blockers* and inform the professor.

## 2. Definition of Done
For any task to be considered complete, the following criteria must be met:
1. Deliverable is written up on the task page (e.g., markdown files in this repo).
2. Code is pushed to the repository.
3. Sources are logged in the Resources/Papers page.
4. Deadline is confirmed and met.
5. Open questions are listed clearly.

## 3. Weekly Log
Post a short update every week. Newest entry at the top. **Five lines is enough.**

### Example Weekly Log Template
**Week of [Date]**
- [Accomplishment 1]
- [Accomplishment 2]
- [Blocker or Challenge]
- [Next Step for upcoming week]

## 4. Resources and Papers
Log every paper, simulator doc, repo, and dataset.
For papers **already read**: Add title, link, and 2-3 lines on what they *actually* do. 
*Rule:* Confirm with the professor before you start reading anything else.

## 5. Daily Routine & Workflow
To maintain a high-quality, professional workflow, follow this exact sequence every day:

### Morning (Planning Phase)
1. **Check Task Tracker:** Open your main Task Tracker (e.g., Notion) and review your current active task.
2. **Set the Day's Goal:** Define a small, achievable sub-task for today (e.g., "Install Isaac Sim and run the default demo").
3. **Pull Latest Changes:** Run `git pull origin main` in your repository to ensure your local workspace is up to date.

### Afternoon (Execution Phase)
4. **Focused Work:** Work on your task. Remember to keep the *Definition of Done* in mind.
5. **Log Blockers Immediately:** If you are stuck for more than 1-2 hours on an error (e.g., CUDA issue, dependency error), write it down. If the blocker persists for a whole day, immediately update the **Progress / Blockers** column in the Task Tracker and notify the professor.

### Evening (Update & Push Phase)
6. **Commit Code:** Stage your files (`git add .`) and commit your progress with a clear message (`git commit -m "Progress on Task 1: setup base simulation env"`).
7. **Push to Remote:** Run `git push origin main`.
8. **Update Task Tracker:** Update the **Status** (e.g., 'In Progress', 'Blocked', 'Completed') and write a 1-sentence note in **Progress** about what you did today.

> [!IMPORTANT]
> **What goes into the main Git Repo vs. Personal Folder?**
> - **Git Repo (`VLM_Based_Robot_Navigation/`)**: Final reports (`evaluation_report.md`), polished setup notes, actual Python/ROS code, environment configurations (`.yaml`), and `workflow.md`.
> - **Personal Folder (`reference_materials/`)**: Rough scratchpads, temporary screenshots, unpolished chat logs with AI, and large raw videos.
