import os
import sys
import uuid
import subprocess
from pathlib import Path

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_dir))
os.chdir(str(backend_dir))

from app.db.session import SessionLocal, Base, engine
from app.models.project import Project
from app.schemas.sandbox import ExecuteCodeRequest
from app.services.sandbox.sandbox_orchestrator import sandbox_orchestrator
from app.core.config import settings

Base.metadata.create_all(bind=engine)
db = SessionLocal()

try:
    print("=================================================================")
    print("FIXMATE AI — PHASE 9 LIVE DOCKER INTEGRATION VERIFICATION")
    print("=================================================================")

    # 1. Create a dedicated project for live verification
    proj_id = str(uuid.uuid4())
    proj_name = f"Live_Phase9_Verification_{uuid.uuid4().hex[:6]}"
    project = Project(
        id=proj_id,
        name=proj_name,
        normalized_name=proj_name.lower(),
        language="Python",
        description="Live integration test for Phase 9 Secure Sandbox",
    )
    db.add(project)
    db.commit()

    # 2. Setup project workspace directory and write Task 6 test file
    workspace_dir = settings.get_workspace_dir(proj_id)
    test_file_name = "task6_verify.py"
    test_file_path = workspace_dir / test_file_name

    task6_source = (
        'print("FIXMATE PHASE 9 EXECUTION VERIFIED")\n'
        'print("Hello from sandbox")\n'
        '\n'
        'x = 25\n'
        'y = 17\n'
        '\n'
        'print("Addition:", x + y)\n'
        'print("Multiplication:", x * y)\n'
    )
    test_file_path.write_text(task6_source, encoding="utf-8")
    print(f"Project created: {proj_name} (ID: {proj_id})")
    print(f"Test file staged: {test_file_name}")

    # 3. Execute through sandbox orchestrator with REAL DOCKER (no mocks)
    print("\nExecuting code through SandboxOrchestrator into isolated Docker container...")
    req = ExecuteCodeRequest(file_path=test_file_name, code=task6_source)
    res = sandbox_orchestrator.execute_code(db, proj_id, req)

    print("\n--- EXECUTION RESULTS ---")
    print("Status:", res.status)
    print("Exit Code:", res.exit_code)
    print("Timeout:", res.timeout)
    print("Duration (ms):", res.duration_ms)
    print("Runtime Error:", res.runtime_error)
    print("Cleanup Status:", res.cleanup_status)
    print("\n--- CAPTURED STDOUT ---")
    print(res.stdout)
    print("--- CAPTURED STDERR ---")
    print(res.stderr or "(Empty stderr)")

    # 4. Strict assertions matching Task 6 specifications
    expected_stdout = (
        "FIXMATE PHASE 9 EXECUTION VERIFIED\n"
        "Hello from sandbox\n"
        "Addition: 42\n"
        "Multiplication: 425\n"
    )

    assert res.status == "PASSED", f"Expected PASSED, got {res.status}"
    assert res.exit_code == 0, f"Expected exit code 0, got {res.exit_code}"
    assert res.stdout == expected_stdout, f"Stdout mismatch!\nExpected:\n{expected_stdout}\nGot:\n{res.stdout}"
    assert res.timeout is False, "Expected timeout=False"
    assert res.duration_ms > 0, "Expected positive duration"

    # 5. Check container cleanup
    chk = subprocess.run(["docker", "ps", "-a", "--filter", f"name=fixmate-sb-{res.id}"], capture_output=True, text=True)
    assert res.id not in chk.stdout, f"Container fixmate-sb-{res.id} was not cleaned up!"
    print("\nContainer cleanup verified: fixmate-sb container was removed.")

    print("\n=================================================================")
    print("LIVE DOCKER VERIFICATION: ALL TASK 6 REQUIREMENTS SATISFIED 100%!")
    print("=================================================================")

finally:
    # Cleanup project from DB and disk
    try:
        p = db.query(Project).filter(Project.id == proj_id).first()
        if p:
            db.delete(p)
            db.commit()
    except Exception:
        pass
    import shutil
    shutil.rmtree(workspace_dir, ignore_errors=True)
    db.close()
