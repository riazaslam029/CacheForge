#!/usr/bin/env bash
# CacheForge — 3 to 5 Minute Judge Interactive Shell Demo
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

DB_PATH="demo_judge.cforge"
rm -rf "$DB_PATH"

echo "=========================================================================="
echo "          CacheForge — Zero Dependency Embedded Storage Engine           "
echo "=========================================================================="
echo ""

echo "[1/10] Initializing fresh CacheForge database..."
python3 cacheforge.py init "$DB_PATH"
echo ""

echo "[2/10] Inserting key-value records with secondary fields and TTL..."
python3 cacheforge.py set "$DB_PATH" user:1 "Riaz Aslam" --field role=student --field city=Lahore
python3 cacheforge.py set "$DB_PATH" user:2 "Jane Doe" --field role=engineer --field city=London
python3 cacheforge.py set "$DB_PATH" session:xyz "Temporary Token Data" --ttl 3600
python3 cacheforge.py set "$DB_PATH" doc:101 "CacheForge is an embedded persistent key-value engine with search"
echo ""

echo "[3/10] Retrieving record by key..."
python3 cacheforge.py get "$DB_PATH" user:1
echo ""

echo "[4/10] Querying secondary field index (role=student)..."
python3 cacheforge.py query "$DB_PATH" --field role=student
echo ""

echo "[5/10] Executing Full-Text Inverted Search ('embedded search engine')..."
python3 cacheforge.py search "$DB_PATH" "embedded search engine"
echo ""

echo "[6/10] Auditing SHA-256 Data Integrity..."
python3 cacheforge.py verify "$DB_PATH"
echo ""

echo "[7/10] Running Database Statistics (JSON format)..."
python3 cacheforge.py stats "$DB_PATH" --json
echo ""

echo "[8/10] Executing Log Compaction..."
python3 cacheforge.py compact "$DB_PATH"
echo ""

echo "[9/10] Running Zero-Dependency Verification Tool..."
python3 tools/check_dependencies.py
echo ""

echo "[10/10] Executing Crash Recovery & WAL Replay Test..."
python3 tools/crash_test.py
echo ""

echo "=========================================================================="
echo "  ✓ CacheForge Demo Finished Successfully! All checks passed.            "
echo "=========================================================================="
rm -rf "$DB_PATH"
