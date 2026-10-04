"""
Tree-sitter structural feature extractor for Python source code.

Extracts AST-based structural features from student code submissions.
Features are designed to NOT leak misconception labels — they reflect
syntactic/structural properties only, not the reasoning or label.

Usage:
    from ml.src.features.tree_sitter_features import extract_features_from_code
    features = extract_features_from_code(code_str)  # returns dict or None on failure
"""
import logging
from typing import Optional
from collections import defaultdict

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Try importing tree-sitter; degrade gracefully if unavailable.
# ---------------------------------------------------------------------------
try:
    from tree_sitter import Language, Parser
    import tree_sitter_python as tspython
    PY_LANGUAGE = Language(tspython.language())
    _PARSER = Parser(PY_LANGUAGE)
    _TS_AVAILABLE = True
except Exception as _e:
    logger.warning("tree-sitter not available: %s. Structural features will be zeros.", _e)
    _PARSER = None
    _TS_AVAILABLE = False


# ---------------------------------------------------------------------------
# Feature names — every feature must be documented here.
# ---------------------------------------------------------------------------
FEATURE_NAMES = [
    # Code volume
    "total_lines",          # Total newlines in source
    "nonempty_lines",       # Lines that are not blank
    "code_chars",           # Total character count

    # Node-type frequencies (raw AST counts)
    "n_functions",          # function_definition nodes
    "n_calls",              # call nodes (function/method calls)
    "n_for_loops",          # for_statement nodes
    "n_while_loops",        # while_statement nodes
    "n_if_stmts",           # if_statement nodes
    "n_elif_clauses",       # elif_clause nodes
    "n_else_clauses",       # else_clause nodes
    "n_return_stmts",       # return_statement nodes
    "n_assignments",        # assignment nodes (=)
    "n_augmented_assigns",  # augmented_assignment nodes (+=, -=, …)
    "n_comparisons",        # comparison_operator nodes (==, !=, <, >, …)
    "n_boolean_ops",        # boolean_operator nodes (and, or)
    "n_not_ops",            # not_operator nodes
    "n_binary_arith",       # binary_operator nodes (+, -, *, /, …)
    "n_unary_arith",        # unary_operator nodes (-, +, ~)
    "n_class_defs",         # class_definition nodes
    "n_lambda",             # lambda nodes
    "n_list_comps",         # list_comprehension nodes
    "n_dict_comps",         # dictionary_comprehension nodes
    "n_generators",         # generator_expression nodes
    "n_try_stmts",          # try_statement nodes
    "n_except_clauses",     # except_clause nodes
    "n_raise_stmts",        # raise_statement nodes
    "n_assert_stmts",       # assert_statement nodes
    "n_delete_stmts",       # delete_statement nodes
    "n_global_stmts",       # global_statement nodes
    "n_nonlocal_stmts",     # nonlocal_statement nodes
    "n_import_stmts",       # import_statement nodes
    "n_from_imports",       # import_from_statement nodes
    "n_yield_stmts",        # yield / yield_statement nodes
    "n_await_stmts",        # await nodes
    "n_subscripts",         # subscript nodes (list/dict access)
    "n_slices",             # slice nodes (a[x:y])
    "n_attribute_access",   # attribute nodes (obj.attr)
    "n_identifiers",        # identifier nodes (variable refs)
    "n_string_literals",    # string nodes
    "n_integer_literals",   # integer nodes
    "n_float_literals",     # float nodes
    "n_none_literals",      # None nodes
    "n_true_literals",      # True nodes
    "n_false_literals",     # False nodes

    # Structural / nesting metrics
    "max_nesting_depth",    # Maximum nesting depth of any node
    "avg_nesting_depth",    # Average nesting depth (float)
    "loop_nesting_depth",   # Maximum depth of nested loops
    "branch_count",         # Total number of branching points (if/elif/while)
    "n_leaf_nodes",         # Total leaf (terminal) AST nodes
    "n_total_nodes",        # Total AST node count

    # Derived ratios (provide scale-invariant signals)
    "calls_per_function",   # n_calls / (n_functions + 1)
    "loop_to_branch_ratio", # (n_for + n_while) / (n_if + 1)
    "return_density",       # n_return / (n_functions + 1)
    "assignment_density",   # n_assignments / (nonempty_lines + 1)

    # Parsing meta-feature (1 if tree-sitter parse succeeded, 0 otherwise)
    "parse_success",
]

N_FEATURES = len(FEATURE_NAMES)
ZERO_FEATURES = {k: 0.0 for k in FEATURE_NAMES}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _count_nodes(root_node) -> dict:
    """Walk the entire AST once and accumulate node-type counts + depth info."""
    counts = defaultdict(int)
    depth_sum = 0
    depth_count = 0
    max_depth = 0
    max_loop_depth = 0

    _LOOP_TYPES = {"for_statement", "while_statement"}

    def _walk(node, depth: int, loop_depth: int):
        nonlocal depth_sum, depth_count, max_depth, max_loop_depth
        counts[node.type] += 1
        depth_sum += depth
        depth_count += 1
        if depth > max_depth:
            max_depth = depth

        current_loop_depth = loop_depth + (1 if node.type in _LOOP_TYPES else 0)
        if current_loop_depth > max_loop_depth:
            max_loop_depth = current_loop_depth

        for child in node.children:
            _walk(child, depth + 1, current_loop_depth)

    _walk(root_node, 0, 0)

    return {
        "counts": dict(counts),
        "max_depth": max_depth,
        "avg_depth": depth_sum / depth_count if depth_count else 0.0,
        "max_loop_depth": max_loop_depth,
        "leaf_nodes": sum(1 for t, c in counts.items()
                         if t not in {"comment"} and c > 0 and t.endswith(("_literal",)) or
                            t in {"identifier", "integer", "float", "string", "none", "true", "false"}),
        "total_nodes": depth_count,
    }


def _safe_parse(code: str):
    """Return (tree, success_bool). Never raises."""
    if not _TS_AVAILABLE or _PARSER is None:
        return None, False
    try:
        tree = _PARSER.parse(bytes(code, "utf-8"))
        has_errors = tree.root_node.has_error
        return tree, not has_errors
    except Exception as exc:
        logger.debug("tree-sitter parse error: %s", exc)
        return None, False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract_features_from_code(code: str) -> dict:
    """
    Extract structural features from a Python source-code string.

    Returns a dict with keys == FEATURE_NAMES and float values.
    If parsing fails, structural counts are 0 and parse_success == 0.
    This function NEVER raises — it always returns a valid feature dict.

    Parameters
    ----------
    code : str
        Raw Python source code (student submission or generated misconception code).

    Returns
    -------
    dict
        Feature dictionary with N_FEATURES entries (all numeric / float).
    """
    feat = dict(ZERO_FEATURES)  # start with all zeros

    # --- Lexical / volume features (always computable) ---
    lines = code.split("\n")
    feat["total_lines"] = float(len(lines))
    feat["nonempty_lines"] = float(sum(1 for l in lines if l.strip()))
    feat["code_chars"] = float(len(code))

    # --- Tree-sitter structural features ---
    tree, success = _safe_parse(code)
    feat["parse_success"] = 1.0 if success else 0.0

    if tree is not None and success:
        try:
            info = _count_nodes(tree.root_node)
            c = info["counts"]

            # --- AST node counts ---
            feat["n_functions"]        = float(c.get("function_definition", 0))
            feat["n_calls"]            = float(c.get("call", 0))
            feat["n_for_loops"]        = float(c.get("for_statement", 0))
            feat["n_while_loops"]      = float(c.get("while_statement", 0))
            feat["n_if_stmts"]         = float(c.get("if_statement", 0))
            feat["n_elif_clauses"]     = float(c.get("elif_clause", 0))
            feat["n_else_clauses"]     = float(c.get("else_clause", 0))
            feat["n_return_stmts"]     = float(c.get("return_statement", 0))
            feat["n_assignments"]      = float(c.get("assignment", 0))
            feat["n_augmented_assigns"]= float(c.get("augmented_assignment", 0))
            feat["n_comparisons"]      = float(c.get("comparison_operator", 0))
            feat["n_boolean_ops"]      = float(c.get("boolean_operator", 0))
            feat["n_not_ops"]          = float(c.get("not_operator", 0))
            feat["n_binary_arith"]     = float(c.get("binary_operator", 0))
            feat["n_unary_arith"]      = float(c.get("unary_operator", 0))
            feat["n_class_defs"]       = float(c.get("class_definition", 0))
            feat["n_lambda"]           = float(c.get("lambda", 0))
            feat["n_list_comps"]       = float(c.get("list_comprehension", 0))
            feat["n_dict_comps"]       = float(c.get("dictionary_comprehension", 0))
            feat["n_generators"]       = float(c.get("generator_expression", 0))
            feat["n_try_stmts"]        = float(c.get("try_statement", 0))
            feat["n_except_clauses"]   = float(c.get("except_clause", 0))
            feat["n_raise_stmts"]      = float(c.get("raise_statement", 0))
            feat["n_assert_stmts"]     = float(c.get("assert_statement", 0))
            feat["n_delete_stmts"]     = float(c.get("delete_statement", 0))
            feat["n_global_stmts"]     = float(c.get("global_statement", 0))
            feat["n_nonlocal_stmts"]   = float(c.get("nonlocal_statement", 0))
            feat["n_import_stmts"]     = float(c.get("import_statement", 0))
            feat["n_from_imports"]     = float(c.get("import_from_statement", 0))
            feat["n_yield_stmts"]      = float(c.get("yield", 0) + c.get("yield_statement", 0))
            feat["n_await_stmts"]      = float(c.get("await", 0))
            feat["n_subscripts"]       = float(c.get("subscript", 0))
            feat["n_slices"]           = float(c.get("slice", 0))
            feat["n_attribute_access"] = float(c.get("attribute", 0))
            feat["n_identifiers"]      = float(c.get("identifier", 0))
            feat["n_string_literals"]  = float(c.get("string", 0))
            feat["n_integer_literals"] = float(c.get("integer", 0))
            feat["n_float_literals"]   = float(c.get("float", 0))
            feat["n_none_literals"]    = float(c.get("none", 0))
            feat["n_true_literals"]    = float(c.get("true", 0))
            feat["n_false_literals"]   = float(c.get("false", 0))

            # --- Depth / structural metrics ---
            feat["max_nesting_depth"]  = float(info["max_depth"])
            feat["avg_nesting_depth"]  = float(info["avg_depth"])
            feat["loop_nesting_depth"] = float(info["max_loop_depth"])
            feat["branch_count"]       = float(feat["n_if_stmts"] + feat["n_elif_clauses"] + feat["n_while_loops"])
            feat["n_leaf_nodes"]       = float(info["leaf_nodes"])
            feat["n_total_nodes"]      = float(info["total_nodes"])

            # --- Derived ratios ---
            feat["calls_per_function"]   = feat["n_calls"]    / (feat["n_functions"] + 1)
            feat["loop_to_branch_ratio"] = (feat["n_for_loops"] + feat["n_while_loops"]) / (feat["n_if_stmts"] + 1)
            feat["return_density"]       = feat["n_return_stmts"] / (feat["n_functions"] + 1)
            feat["assignment_density"]   = feat["n_assignments"]  / (feat["nonempty_lines"] + 1)

        except Exception as exc:
            logger.warning("Feature extraction error (post-parse): %s", exc)
            # Keep whatever was set; parse_success stays 1 but structural zeros used.

    return feat


def extract_features_batch(codes: list, verbose: bool = False) -> list:
    """
    Extract features for a list of code strings.

    Parameters
    ----------
    codes : list[str]
    verbose : bool
        Log progress every 100 items.

    Returns
    -------
    list[dict]  — one dict per code string, always length == len(codes).
    """
    results = []
    for i, code in enumerate(codes):
        if verbose and i > 0 and i % 100 == 0:
            logger.info("Extracted features for %d / %d samples", i, len(codes))
        results.append(extract_features_from_code(code or ""))
    return results


def features_to_matrix(feature_dicts: list):
    """
    Convert a list of feature dicts → 2D numpy array shaped (N, N_FEATURES).

    Returns (matrix, feature_names).
    """
    import numpy as np
    rows = []
    for fd in feature_dicts:
        rows.append([fd.get(k, 0.0) for k in FEATURE_NAMES])
    return np.array(rows, dtype=float), FEATURE_NAMES
