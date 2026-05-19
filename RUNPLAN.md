# Tkinter System Monitor Plan

# 1. Design the app
/asksubagent plan "Design a Python TUI app that shows system information, cpu ,cores,memory,network and running processes in a clean dashboard."

# 2. Review the approach
/asksubagent review "Review the planned system monitor layout for portability, maintainability, and testability."

# 3. Create the project layout in small scoped steps
/asksubagent worker --scope . "Create only the folder structure and minimal starter files: app.py, system_info.py, ui.py, requirements.txt, README.md, and tests/. Keep each file minimal."
/asksubagent worker --file app.py "Implement app entrypoint and main loop wiring for the TUI."
/asksubagent worker --file system_info.py "Implement system metrics collection: cpu, cores, memory, network, and running processes."
/asksubagent worker --file ui.py "Implement dashboard UI and bind UI refresh/update to system_info functions."
/asksubagent worker --file README.md "Update README with setup and run instructions for the system monitor app."

# 4. Final review
/asksubagent review "Review the finished app system monitor project for bugs, missing files, and usability issues."

# 5. Tests
/asksubagent search "Locate current test framework and test entrypoints in this project."
/asksubagent review "Propose a minimal unit test plan with target files and edge cases."
/asksubagent worker --scope tests "Create unit tests under tests subfolder only, following the plan. For new files, use start_line=0 and end_line=0 with the full file contents."
/asksubagent worker --scope tests "If a test runner script is needed, create it under tests subfolder only and run the tests."  
