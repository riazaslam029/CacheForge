"""
CacheForge Python Library Usage Example.
Demonstrates setting records, TTL, secondary fields, full-text search, and compaction.
"""

from cacheforge import CacheForgeDB, KeyNotFoundError

def main():
    print("=== CacheForge Python API Usage Demo ===")
    
    # 1. Initialize Database Engine
    db = CacheForgeDB("./demo_db.cforge")
    print(f"✓ Opened database at: {db.db_dir}")

    # 2. Store Records with Secondary Fields & TTL
    db.set("user:101", "Riaz Aslam", fields={"role": "student", "city": "Lahore"})
    db.set("user:102", "Jane Doe", fields={"role": "engineer", "city": "London"})
    db.set("session:abc", "Active Session Data", ttl=60.0)

    # 3. Get and Query
    user1 = db.get("user:101")
    print(f"User 101: {user1.value_str} (Fields: {user1.fields})")

    students = db.query({"role": "student"})
    print(f"Students found: {[s.key for s in students]}")

    # 4. Full-Text Search
    db.set("article:1", "CacheForge is a high performance zero dependency embedded storage engine in Python")
    search_matches = db.search("zero dependency database engine")
    print("\nSearch Results for 'zero dependency database engine':")
    for rec, score in search_matches:
        print(f"  [{score:.4f}] {rec.key} -> {rec.value_str}")

    # 5. Database Statistics & Integrity
    stats = db.stats()
    print(f"\nLive Records: {stats['live_records']} | Data Size: {stats['data_size_bytes']} B")

    integrity = db.verify()
    print(f"Data Integrity: {integrity.index_status}")

    db.close()
    print("\n✓ Closed database successfully.")

if __name__ == "__main__":
    main()
