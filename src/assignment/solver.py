from ortools.sat.python import cp_model
from .models import ProblemInput, CriterionType, AssignmentResult, ProblemOutput, ProblemStats, RankingsStats, MinimizeCriterionStats

# ortools works on integer values
SCALING_FACTOR = 1000

def _compute_stats(data: ProblemInput, assignments):
    student_map = {s.id: s for s in data.students}
    group_students = {g.id: [] for g in data.groups}
    for assignment in assignments:
        group_students.setdefault(assignment.group_id, []).append(assignment.student_id)

    rankings_stats = None
    if any(s.rankings for s in data.students):
        rank_values = []
        for assignment in assignments:
            student = student_map.get(assignment.student_id)
            if not student or not student.rankings:
                continue
            rank_values.append(student.rankings.get(assignment.group_id, 0.0))
        if rank_values:
            rankings_stats = RankingsStats(
                avg_rank=sum(rank_values) / len(rank_values),
                min_rank=min(rank_values),
            )

    minimize_groups = {}
    for g in data.groups:
        for c_name, configs in g.criteria.items():
            if any(c.type == CriterionType.MINIMIZE for c in configs):
                minimize_groups.setdefault(c_name, []).append(g.id)

    minimize_stats = None
    if minimize_groups:
        minimize_stats = {}
        for c_name, group_ids in minimize_groups.items():
            if data.students:
                global_mean = sum(s.values.get(c_name, 0) for s in data.students) / len(data.students)
            else:
                global_mean = 0.0

            group_avgs = []
            for g_id in group_ids:
                student_ids = group_students.get(g_id, [])
                if not student_ids:
                    continue
                total = sum(student_map[s_id].values.get(c_name, 0) for s_id in student_ids)
                group_avgs.append(total / len(student_ids))

            if len(group_avgs) >= 2:
                max_group_avg_diff = max(group_avgs) - min(group_avgs)
            else:
                max_group_avg_diff = 0.0

            if group_avgs:
                max_group_global_diff = max(abs(avg - global_mean) for avg in group_avgs)
            else:
                max_group_global_diff = 0.0

            minimize_stats[c_name] = MinimizeCriterionStats(
                max_group_avg_diff=max_group_avg_diff,
                max_group_global_diff=max_group_global_diff,
            )

    if not rankings_stats and not minimize_stats:
        return None

    return ProblemStats(rankings=rankings_stats, minimize=minimize_stats)

def solve_assignment(data: ProblemInput) -> ProblemOutput:
    model = cp_model.CpModel()
    
    # x[s, g] is true if student s is assigned to group g
    x = {}
    for s in data.students:
        for g_id in s.possible_groups:
            x[s.id, g_id] = model.NewBoolVar(f'x_s{s.id}_g{g_id}')
            
    # Each student is assigned to exactly one group
    for s in data.students:
        model.Add(sum(x[s.id, g_id] for g_id in s.possible_groups) == 1)
        
    # Group size constraints
    for g in data.groups:
        relevant_student_vars = [x[s.id, g.id] for s in data.students if g.id in s.possible_groups]
        if not relevant_student_vars:
             # If no students can be in this group but size > 0, it's infeasible
             if g.size > 0:
                 return ProblemOutput(assignments=[], status="INFEASIBLE")
             continue
        model.Add(sum(relevant_student_vars) == g.size)
        
    # Exclusion constraints: forbidden pairs cannot be in the same group
    for pair in data.exclude:
        if len(pair) < 2:
            continue
        s1, s2 = pair[0], pair[1]
        for g in data.groups:
            if (s1, g.id) in x and (s2, g.id) in x:
                model.Add(x[s1, g.id] + x[s2, g.id] <= 1)
        
    penalties = []
    has_rankings = any(s.rankings for s in data.students)

    # Global mean per criterion (used for MINIMIZE targets).
    criterion_names = set()
    for g in data.groups:
        criterion_names.update(g.criteria.keys())

    global_means = {}
    if data.students:
        for c_name in criterion_names:
            total = sum(s.values.get(c_name, 0) for s in data.students)
            global_means[c_name] = total / len(data.students)
    else:
        for c_name in criterion_names:
            global_means[c_name] = 0.0
    
    # Criteria constraints and objectives
    for g in data.groups:
        for c_name, configs in g.criteria.items():
            relevant_students = [s for s in data.students if g.id in s.possible_groups]
            if not relevant_students:
                continue
                
            # Scaled values
            scaled_vals = {s.id: int(s.values.get(c_name, 0) * SCALING_FACTOR) for s in relevant_students}
            
            # group_sum = sum(scaled_val * x)
            group_sum = model.NewIntVar(0, SCALING_FACTOR * g.size, f'sum_{g.id}_{c_name}')
            model.Add(group_sum == sum(scaled_vals[s_id] * x[s_id, g.id] for s_id in scaled_vals))
            
            for c_config in configs:
                if c_config.type == CriterionType.MINIMIZE:
                    # target_sum = global_mean * group_size * SCALING_FACTOR
                    target_sum = int(global_means.get(c_name, 0) * g.size * SCALING_FACTOR)

                    # Penalize deviation from target to encourage even spread.
                    diff = model.NewIntVar(-SCALING_FACTOR * g.size, SCALING_FACTOR * g.size, f'diff_{g.id}_{c_name}_{c_config.type}')
                    model.Add(diff == group_sum - target_sum)

                    # penalty = |diff|
                    penalty = model.NewIntVar(0, SCALING_FACTOR * g.size, f'p_{g.id}_{c_name}_{c_config.type}')
                    model.AddAbsEquality(penalty, diff)
                    penalties.append(penalty)

                elif c_config.type == CriterionType.PULL:
                    max_val = max(scaled_vals.values()) if scaled_vals else 0
                    max_sum = max_val * g.size
                    penalty = model.NewIntVar(0, max_sum, f'p_{g.id}_{c_name}_{c_config.type}')
                    model.Add(penalty == max_sum - group_sum)
                    penalties.append(penalty)

                elif c_config.type == CriterionType.PREREQUISITE:
                    if c_config.min_ratio is None:
                        continue
                    threshold = int(c_config.min_ratio * SCALING_FACTOR)

                    # Any student below threshold cannot be in this group
                    for s_id, s_val in scaled_vals.items():
                        if s_val < threshold:
                            model.Add(x[s_id, g.id] == 0)

    # Rankings objective (maximize total ranking, normalized to avoid dominance)
    if has_rankings:
        ranking_scale = max(1, SCALING_FACTOR // max(1, len(criterion_names)))
        ranking_terms = []
        for s in data.students:
            if not s.rankings:
                continue
            for g_id in s.possible_groups:
                rank_val = s.rankings.get(g_id, 0.0)
                scaled_rank = int(rank_val * ranking_scale)
                if (s.id, g_id) in x and scaled_rank:
                    ranking_terms.append(scaled_rank * x[s.id, g_id])
        ranking_sum = model.NewIntVar(0, ranking_scale * len(data.students), "ranking_sum")
        model.Add(ranking_sum == sum(ranking_terms) if ranking_terms else 0)
        ranking_penalty = model.NewIntVar(0, ranking_scale * len(data.students), "ranking_penalty")
        model.Add(ranking_penalty == ranking_scale * len(data.students) - ranking_sum)
        penalties.append(ranking_penalty)

    # Minimize sum of penalties
    if penalties:
        model.Minimize(sum(penalties))
    
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        assignments = []
        for (s_id, g_id), var in x.items():
            if solver.Value(var):
                assignments.append(AssignmentResult(student_id=s_id, group_id=g_id))
        assignments.sort(key=lambda a: a.student_id)
        stats = _compute_stats(data, assignments)
        return ProblemOutput(assignments=assignments, status=solver.StatusName(status), stats=stats)
    else:
        return ProblemOutput(assignments=[], status=solver.StatusName(status))
