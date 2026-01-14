from ortools.sat.python import cp_model
from .models import ProblemInput, CriterionType, AssignmentResult, ProblemOutput

# ortools works on integer values
SCALING_FACTOR = 10000

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
    
    # Criteria constraints and objectives
    for g in data.groups:
        for c_name, c_config in g.criteria.items():
            relevant_students = [s for s in data.students if g.id in s.possible_groups]
            if not relevant_students:
                continue
                
            # Scaled values
            scaled_vals = {s.id: int(s.values.get(c_name, 0) * SCALING_FACTOR) for s in relevant_students}
            
            # group_sum = sum(scaled_val * x)
            group_sum = model.NewIntVar(0, SCALING_FACTOR * g.size, f'sum_{g.id}_{c_name}')
            model.Add(group_sum == sum(scaled_vals[s_id] * x[s_id, g.id] for s_id in scaled_vals))
            
            if c_config.type == CriterionType.CONSTRAINT:
                if c_config.min_ratio is None:
                    continue
                # threshold = min_ratio * group_size * SCALING_FACTOR
                threshold = int(c_config.min_ratio * g.size * SCALING_FACTOR)
                model.Add(group_sum >= threshold)
                
            elif c_config.type == CriterionType.MINIMIZE:
                if c_config.target is None:
                    continue
                # target_sum = target * group_size * SCALING_FACTOR
                target_sum = int(c_config.target * g.size * SCALING_FACTOR)
                
                # penalty = max(0, group_sum - target_sum)
                diff = model.NewIntVar(-SCALING_FACTOR * g.size, SCALING_FACTOR * g.size, f'diff_{g.id}_{c_name}')
                model.Add(diff == group_sum - target_sum)
                
                penalty = model.NewIntVar(0, SCALING_FACTOR * g.size, f'p_{g.id}_{c_name}')
                model.AddMaxEquality(penalty, [0, diff])
                
                # penalty_sq = penalty * penalty
                penalty_sq = model.NewIntVar(0, (SCALING_FACTOR * g.size)**2, f'psq_{g.id}_{c_name}')
                model.AddMultiplicationEquality(penalty_sq, [penalty, penalty])
                penalties.append(penalty_sq)
                
            elif c_config.type == CriterionType.MAXIMIZE:
                if c_config.target is None:
                    continue
                target_sum = int(c_config.target * g.size * SCALING_FACTOR)
                
                # penalty = max(0, target_sum - group_sum)
                diff = model.NewIntVar(-SCALING_FACTOR * g.size, SCALING_FACTOR * g.size, f'diff_{g.id}_{c_name}')
                model.Add(diff == target_sum - group_sum)
                
                penalty = model.NewIntVar(0, SCALING_FACTOR * g.size, f'p_{g.id}_{c_name}')
                model.AddMaxEquality(penalty, [0, diff])
                
                penalty_sq = model.NewIntVar(0, (SCALING_FACTOR * g.size)**2, f'psq_{g.id}_{c_name}')
                model.AddMultiplicationEquality(penalty_sq, [penalty, penalty])
                penalties.append(penalty_sq)

    # Minimize sum of squared penalties
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
        return ProblemOutput(assignments=assignments, status=solver.StatusName(status))
    else:
        return ProblemOutput(assignments=[], status=solver.StatusName(status))
