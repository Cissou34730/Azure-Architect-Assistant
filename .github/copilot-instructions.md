<!-- Use this file to provide workspace-specific custom instructions to Copilot. For more details, visit https://code.visualstudio.com/docs/copilot/copilot-customization#_use-a-githubcopilotinstructionsmd-file -->
- [x] Verify that the copilot-instructions.md file in the .github directory is created.

- [x] Clarify Project Requirements
	Azure Architect assistant. There are 4 main features. Project to describe the project we want to build an architecutre on. Chat with technical documentation. Manage the technical document build a RAG and generate an architecture document and IaC code.
	The frontend is TypeScript React, backend in Python.
	
	[x] Mandatory rules to follow before writing code:
	- Use descriptive variable names (days_until_expiration vs d) and clear logic. If you need a comment to explain what the code does, the code is likely too complex.
	- DRY (Don't Repeat Yourself): If you copy-paste code, you create a maintenance debt. Abstract duplicate logic into a single function or class so you only have to fix bugs in one place
	- Avoid over-engineering. The simplest solution that solves the problem is usually the best. Complexity increases the surface area for bugs
	- Do not add functionality until it is necessary. Speculative coding leads to unused, unmaintained bloat
	- Single Responsibility Principle (SRP): A function, class, or module should have one, and only one, reason to change. THE MOST IMPORTANT RULE FOR YOU
	- Never trust data coming from outside your system (user input, API responses). Always validate types
	- Version control (Git) is a save point. Make small, descriptive commits that fix one thing at a time

	[x] Technical Stack Requirements:
	- React 19+ with TypeScript
	- Use TypeScript 5+
	- Use only TailwindCSS 4.1 for Styling
	- Backend in Python 3.10+
	- Vite for frontend build tool

	[x] Code Style and Conventions:
	- Liting: ESLint with recommended settings for TypeScript and React
	- Formatting: Prettier with default settings
	- Python: Follow PEP 8 style guide for Python code
	- Not hardcoding values. Use configuration files where appropriate.

	[X] Project Structure:
	- Frontend and backend code should be in separate folders at the root level.
	- Use a monorepo structure to manage both frontend and backend codebases.
	- Place new file in appropriate directories based on their functionality.
	- Prefer composable and small modules functions
	- All documents and md file except README.md must go to /docs in the relevant folders

	[x] What to avoid
	- Indroduce any new frameworks or libraries unless absolutely necessary and without consent

- [x] Scaffold the Project
	<!--
	Ensure that the previous step has been marked as completed.
	Call project setup tool with projectType parameter.
	Run scaffolding command to create project files and folders.
	Use '.' as the working directory.
	If no appropriate projectType is available, search documentation using available tools.
	Otherwise, create the project structure manually using available file creation tools.
	-->

- [x] Customize the Project
	
	Verify that all previous steps have been completed successfully and you have marked the step as completed.
	Develop a plan to modify codebase according to user requirements.
	Apply modifications using appropriate tools and user-provided references.
	Skip this step for "Hello World" projects.
	

- [x] Install Required Extensions
	<!-- ONLY install extensions provided mentioned in the get_project_setup_info. Skip this step otherwise and mark as completed. -->

- [x] Compile the Project
	<!--
	Verify that all previous steps have been completed.
	Install any missing dependencies.
	Run diagnostics and resolve any issues.
	Check for markdown files in project folder for relevant instructions on how to do this.
	-->

- [x] Create and Run Task

- [x] Launch the Project

- [x] Ensure Documentation is Complete

- [x] Ensuire module and library have a clean 

- Work through each checklist item systematically.
- Keep communication concise and focused.
- Follow development best practices.
