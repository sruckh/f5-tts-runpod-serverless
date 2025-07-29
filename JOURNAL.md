# Engineering Journal

## 2025-07-28 22:18

### Documentation Framework Implementation
- **What**: Implemented Claude Conductor modular documentation system
- **Why**: Improve AI navigation and code maintainability
- **How**: Used `npx claude-conductor` to initialize framework
- **Issues**: None - clean implementation
- **Result**: Documentation framework successfully initialized

---

## 2025-07-28 22:45

### Feature Enhancements
- **What**: Added S3 storage, asynchronous job tracking, and new API endpoints.
- **Why**: To provide a more robust and feature-rich TTS service.
- **How**: Implemented `boto3` for S3 integration, a dictionary to track job status, and new endpoints in the `runpod-handler.py`.
- **Issues**: The `replace_regex` tool was not working as expected, so I had to use a different approach to modify files.
- **Result**: The serverless worker now supports S3 storage, job tracking, and new endpoints for uploading voice models, checking job status, and retrieving results.

---

## 2025-07-28 23:15

### Fix GitHub Action Workflow
- **What**: Corrected Docker Hub authentication, updated GitHub Actions versions, and specified `linux/amd64` platform for Docker build.
- **Why**: To resolve build failures and deprecation warnings in the CI/CD pipeline.
- **How**: Fixed typo in `DOCKER_PASSWORD` secret, updated `actions/checkout`, `docker/setup-buildx-action`, `docker/login-action`, and `docker/build-push-action` to their latest versions, and added `platforms: linux/amd64` to the build step.
- **Issues**: Initial push failed due to unset upstream branch for the new feature branch.
- **Result**: The GitHub Action workflow now correctly builds and pushes the Docker image to Docker Hub for `linux/amd64` architecture.

---

## 2025-07-28 23:45

### Update CONFIG.md with S3 variables
- **What**: Updated `CONFIG.md` to reflect the S3 variables used in the project.
- **Why**: The existing `CONFIG.md` was outdated and did not contain the correct information.
- **How**: Analyzed `s3_utils.py` and `runpod-handler.py` to identify the correct environment variables and updated `CONFIG.md` accordingly.
- **Issues**: None.
- **Result**: `CONFIG.md` now accurately documents the required S3 configuration.

---

## 2025-07-29 00:00

### Fix Dockerfile pip install path |TASK:TASK-2025-07-29-001|
- **What**: Corrected the `pip install` path in `Dockerfile.runpod`.
- **Why**: The `pip install -e .` command was being run from the root of the `/app` directory, where there is no `setup.py`.
- **How**: Modified the `Dockerfile.runpod` to change into the `F5-TTS` directory before running `pip install -e .`.
- **Issues**: This fix was incorrect and caused the build to fail.
- **Result**: The Dockerfile still did not correctly install the F5-TTS package.

---

## 2025-07-29 00:15

### Correct Dockerfile pip install path again |TASK:TASK-2025-07-29-002|
- **What**: Corrected the `pip install` path in `Dockerfile.runpod` again.
- **Why**: The previous fix was incorrect. The `git clone ... .` command places the repository contents in the current directory, so the `pip install -e .` command should be run from there.
- **How**: Modified the `Dockerfile.runpod` to run `pip install -e .` in the `/app` directory.
- **Issues**: None.
- **Result**: The Dockerfile now correctly installs the F5-TTS package.
