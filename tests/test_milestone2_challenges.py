"""
Milestone 2 Verification Test Suite: Challenge Environment (Doors 1 & 2)
========================================================================
Validates:
1. Deterministic HMAC-SHA256 seed derivation per team.
2. Door 1 (Filesystem Investigation) generation, structure, and solvability.
3. Door 2 (Hidden Files & Hexadecimal Decoding) generation and solvability.
4. Cross-team isolation and randomization (Team 1 vs Team 2 vs Team 3).
5. Reproducibility (re-running generation for Team 1 yields identical challenges).
"""

import sys
import shutil
import tempfile
from pathlib import Path

# Add challenge scripts to Python path
scripts_path = Path(__file__).resolve().parent.parent / "challenge-environment" / "scripts"
sys.path.insert(0, str(scripts_path))

import pytest
from generate_challenges import ChallengeGenerator, derive_team_seed


@pytest.fixture
def temp_env():
    """Create a temporary root filesystem sandbox for testing."""
    temp_dir = Path(tempfile.mkdtemp(prefix="escape_test_"))
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_01_deterministic_seed_derivation():
    """Verify that seeds are deterministic per team and differ across teams."""
    seed_team1_a = derive_team_seed(team_id=1, competition_id="escape2026", server_secret="test_secret")
    seed_team1_b = derive_team_seed(team_id=1, competition_id="escape2026", server_secret="test_secret")
    seed_team2 = derive_team_seed(team_id=2, competition_id="escape2026", server_secret="test_secret")

    # Identical inputs must yield identical seeds
    assert seed_team1_a == seed_team1_b, "Seed generation is not deterministic!"
    # Different team IDs must yield different seeds
    assert seed_team1_a != seed_team2, "Different teams must have distinct seeds!"
    print("\n[VERIFIED] 1. Deterministic HMAC-SHA256 seeding verified.")


def test_02_door_1_filesystem_structure_and_solve(temp_env):
    """
    Verify Door 1:
    - /home/player directory tree and README.txt
    - /escape/room1 sectors and clue placement
    - Solvability via simulated 'find' command
    """
    gen = ChallengeGenerator(team_id=1, root_dir=temp_env, server_secret="test_secret")
    answers = gen.generate_all()

    home = temp_env / "home" / "player"
    escape = temp_env / "escape" / "room1"

    # Verify home directories
    for d in ["documents", "downloads", "logs", "old", "tmp"]:
        assert (home / d).is_dir(), f"Missing expected directory: {d}"

    assert (home / "README.txt").is_file(), "Missing /home/player/README.txt"
    readme_text = (home / "README.txt").read_text(encoding="utf-8")
    assert "/escape" in readme_text

    # Simulate player searching for clues: find /escape -type f -name "*.txt"
    txt_files = list(escape.rglob("*.txt"))
    assert len(txt_files) >= 2, "Expected multiple sector files in /escape/room1"

    # Find the real clue
    clue_file = None
    for f in txt_files:
        if f.name == "clue.txt":
            clue_file = f
            break

    assert clue_file is not None, "clue.txt was not generated in target sector!"
    clue_content = clue_file.read_text(encoding="utf-8")
    
    expected_flag = answers["door1"]["flag"]
    assert expected_flag in clue_content
    assert expected_flag.startswith("ESCAPE{DOOR1_SECTOR_")
    print(f"[VERIFIED] 2. Door 1 verified (Target: {answers['door1']['target_path']}, Flag: {expected_flag})")


def test_03_door_2_hidden_files_and_hex_decode(temp_env):
    """
    Verify Door 2:
    - Multiple hidden dotfiles in /home/player
    - Presence of decoys
    - Target hidden file with hexadecimal sequence
    - Solvability by decoding hex to plaintext and forming flag
    """
    gen = ChallengeGenerator(team_id=1, root_dir=temp_env, server_secret="test_secret")
    answers = gen.generate_all()

    home = temp_env / "home" / "player"
    
    # Locate all hidden files in /home/player
    hidden_files = [f for f in home.iterdir() if f.name.startswith(".") and f.is_file()]
    assert len(hidden_files) >= 5, f"Expected at least 5 hidden files, found {len(hidden_files)}"

    # Find the target hidden file containing the hex bypass fragment
    target_info = answers["door2"]
    target_filename = Path(target_info["target_file"]).name
    target_file = home / target_filename
    assert target_file.is_file(), f"Target hidden file {target_filename} not found!"

    content = target_file.read_text(encoding="utf-8")
    assert target_info["hex_sequence"] in content

    # Simulate player hex decoding: xxd -r -p or bytes.fromhex
    hex_clean = target_info["hex_sequence"].replace(" ", "").strip()
    decoded_bytes = bytes.fromhex(hex_clean)
    decoded_plaintext = decoded_bytes.decode("utf-8")

    assert decoded_plaintext == target_info["plaintext"]
    solved_flag = f"ESCAPE{{DOOR2_{decoded_plaintext}}}"
    assert solved_flag == target_info["flag"]
    print(f"[VERIFIED] 3. Door 2 verified (Hidden File: {target_filename}, Decoded: {decoded_plaintext}, Flag: {solved_flag})")


def test_04_cross_team_randomization(temp_env):
    """Verify that different teams receive different sectors, hex values, and flags."""
    env_t1 = temp_env / "t1"
    env_t2 = temp_env / "t2"

    gen1 = ChallengeGenerator(team_id=1, root_dir=env_t1, server_secret="secret")
    ans1 = gen1.generate_all()

    gen2 = ChallengeGenerator(team_id=2, root_dir=env_t2, server_secret="secret")
    ans2 = gen2.generate_all()

    # Door 1 flags and locations must differ
    assert ans1["door1"]["flag"] != ans2["door1"]["flag"]
    
    # Door 2 hex sequences, plaintexts, and flags must differ
    assert ans1["door2"]["flag"] != ans2["door2"]["flag"]
    assert ans1["door2"]["hex_sequence"] != ans2["door2"]["hex_sequence"]
    assert ans1["door2"]["plaintext"] != ans2["door2"]["plaintext"]
    print("[VERIFIED] 4. Cross-team isolation & randomization confirmed (Team 1 vs Team 2 differ).")


def test_05_reproducibility_after_reset(temp_env):
    """Verify that recreating an environment for the same team produces the exact same puzzle."""
    env_a = temp_env / "run_a"
    env_b = temp_env / "run_b"

    gen_a = ChallengeGenerator(team_id=42, root_dir=env_a, server_secret="fixed_secret")
    ans_a = gen_a.generate_all()

    gen_b = ChallengeGenerator(team_id=42, root_dir=env_b, server_secret="fixed_secret")
    ans_b = gen_b.generate_all()

    assert ans_a == ans_b, "Regenerated challenge state for same team must match exactly!"
    print("[VERIFIED] 5. Deterministic reset & recovery confirmed (Team 42 matches exactly across runs).")


if __name__ == "__main__":
    pytest.main(["-v", "-s", __file__])
