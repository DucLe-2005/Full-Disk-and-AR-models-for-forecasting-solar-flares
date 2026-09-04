from sklearn.metrics import confusion_matrix as sklearn_confusion_matrix


def confusion_matrix(true_labels, predicted_labels) -> dict[str, int]:
    """Return confusion-matrix counts in TN, FP, FN, TP order."""
    tn, fp, fn, tp = sklearn_confusion_matrix(true_labels,
        predicted_labels,
        labels=[0, 1],
    ).ravel()

    return {
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "tp": tp,
    }


def accuracy(matrix: dict[str, float]) -> float:
    # out of all predictions, how many I got right
    total = sum(matrix.values())
    return (matrix["tp"] + matrix["tn"]) / total if total else 0.0


def precision(matrix: dict[str, float]) -> float:
    # out of the positive predictions, how many I got right
    denominator = matrix["tp"] + matrix["fp"]
    return matrix["tp"] / denominator if denominator else 0.0


def recall(matrix: dict[str, float]) -> float:
    # out of all positive flare events, how many I did predict positive
    denominator = matrix["tp"] + matrix["fn"]
    return matrix["tp"] / denominator if denominator else 0.0


def f1(matrix: dict[str, float]) -> float:
    # how good is the balance between precision and recall
    score_precision = precision(matrix)
    score_recall = recall(matrix)
    denominator = score_precision + score_recall
    return 2 * score_precision * score_recall / denominator if denominator else 0.0


def tss(matrix: dict[str, float]) -> float:
    """True skill statistic: true-positive rate minus false-positive rate."""
    tp, tn, fp, fn = matrix["tp"], matrix["tn"], matrix["fp"], matrix["fn"]
    tp_rate = tp / float(tp + fn) if tp + fn else 0
    fp_rate = fp / float(fp + tn) if fp + tn else 0
    
    TSS = tp_rate - fp_rate
    
    return TSS

def hss(matrix: dict[str, float]) -> float:
    tp, tn, fp, fn = matrix["tp"], matrix["tn"], matrix["fp"], matrix["fn"]
    
    n = tn + fp
    p = tp + fn
    denominator = p * (fn + tn) + (tp + fp) * n
    HSS = 2 * (tp * tn - fn * fp) / float(denominator) if denominator else 0.0
    
    return HSS
