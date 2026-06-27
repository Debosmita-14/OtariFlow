from backend import store

create_request = store.create_request
deduct_budget = store.deduct_budget
reset_budget = store.reset_budget
log_attack = store.log_attack
update_model_metrics = store.update_model_metrics
get_recent_requests = store.get_recent_requests
get_recent_attacks = store.get_recent_attacks
get_model_metrics = store.get_model_metrics
get_budget = store.get_budget
get_stats = store.get_stats
get_cache_entries = store.get_cache_entries
get_cache_stats = store.get_cache_stats
