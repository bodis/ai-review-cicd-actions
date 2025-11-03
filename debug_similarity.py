#!/usr/bin/env python3
"""Debug similarity calculation."""

def check_similarity(msg1, msg2):
    """Check word overlap similarity."""
    stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}

    words1 = set(msg1.lower().split()) - stop_words
    words2 = set(msg2.lower().split()) - stop_words

    if not words1 or not words2:
        return 0.0

    intersection = len(words1 & words2)
    union = len(words1 | words2)

    similarity = intersection / union if union > 0 else 0

    print(f"\nMessage 1: {msg1}")
    print(f"Message 2: {msg2}")
    print(f"Words 1: {words1}")
    print(f"Words 2: {words2}")
    print(f"Intersection: {words1 & words2}")
    print(f"Union size: {union}")
    print(f"Similarity: {similarity:.2f} ({'MATCH' if similarity > 0.7 else 'NO MATCH'})")

    return similarity

# Test SQL injection messages
print("=" * 80)
print("SQL INJECTION MESSAGES")
print("=" * 80)
check_similarity(
    "🔒 Critical SQL Injection Risk",
    "🔒 CRITICAL: SQL Injection vulnerability"
)
check_similarity(
    "🔒 Critical SQL Injection Risk",
    "SQL injection vulnerability: User input (pr_number and status) is directly concatenated into SQL query"
)

# Test resource leak messages
print("\n" + "=" * 80)
print("RESOURCE LEAK MESSAGES")
print("=" * 80)
check_similarity(
    "Resource Leak - No Connection Cleanup",
    "Resource leak: Database connection not closed"
)

# Test dead code messages
print("\n" + "=" * 80)
print("DEAD CODE MESSAGES")
print("=" * 80)
check_similarity(
    "✨ Dead code: Method never called",
    "Orphaned method breaks orchestrator pattern"
)
