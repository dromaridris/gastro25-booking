"""@mention parse and notify helpers."""

from gi_platform.user_mention_service import parse_mentions, process_mentions, process_mentions_diff

assert parse_mentions('Please review @omar and @sara') == ['omar', 'sara']
assert parse_mentions('@user1,@user2') == ['user1', 'user2']

print('Mention service tests passed')
