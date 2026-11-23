"""B7 - Phat hien ghe bi giu cho bat thuong bang IsolationForest (CONTRACT: hog_score / hog_anomaly).

Moi AI_INTERVAL_SEC (5 phut) gateway nhin lai AI_WINDOW_SEC (30 phut) du lieu da luu trong SQLite,
rut ra 4 dac trung cho tung ghe roi hoi mo hinh "cua so nay co binh thuong khong".

LUU Y TRUNG THUC (ghi vao bao cao): chua co du lieu that dai ngay, nen mo hinh duoc HUAN LUYEN
TREN DU LIEU GIA LAP cua hanh vi binh thuong (xem synth_normal). IsolationForest chi hoc "binh thuong
trong; cai gi lech xa la bat thuong", khong can nhan 'giu cho' khi huan luyen.

Chay thu (khong can CoreIOT, khong can .env):   python ai_job.py --demo
Chay tren du lieu that trong gateway.db:         python ai_job.py --once
Huan luyen lai:                                  python ai_job.py --retrain
"""
#mỗi 5 phút nhìn lại 30 phút dữ liệu của từng ghế, rút ra 4 con số (số lần để đồ, tổng giây để đồ...) 
#rồi hỏi mô hình IsolationForest “có bất thường không”. Kết quả gửi lên CoreIOT dưới tên hog_score và hog_anomaly
import argparse
import logging
import time

import joblib
import numpy as np
from sklearn.ensemble import IsolationForest

log = logging.getLogger("ai")

FEATURES = ["n_object_entries", "object_secs_total", "obj_secs_max", "occupied_ratio"]
MIN_SAMPLES = 6          # it hon 6 ban tin (~1 phut) thi khong du de ket luan
RANDOM_STATE = 42


# ---------------------------------------------------------------- dac trung
def window_features(rows):
    """rows: list dict (ts, state, obj_secs) da sap theo ts, thuoc 1 ghe trong 1 cua so.
    Tra ve list 4 so theo FEATURES, hoac None neu du lieu qua it."""
    if len(rows) < MIN_SAMPLES:
        return None

    entries = 0                  # so lan chuyen vao OBJECT_ONLY
    total = 0.0                  # tong giay OBJECT_ONLY (cong cac "dot" lai)
    obj_max = 0
    occupied = 0
    prev_state = None
    ep_obj = 0                   # obj_secs lon nhat trong dot OBJECT_ONLY dang chay
    ep_first_ts = ep_last_ts = None

    def close_episode():
        nonlocal total, ep_obj, ep_first_ts, ep_last_ts
        if ep_first_ts is not None:
            by_clock = (ep_last_ts - ep_first_ts) / 1000.0
            total += ep_obj if ep_obj > 0 else by_clock    # uu tien so giay do tren node
        ep_obj, ep_first_ts, ep_last_ts = 0, None, None

    for r in rows:
        st = r["state"]
        o = r["obj_secs"] or 0
        obj_max = max(obj_max, o)
        if st == "OCCUPIED":
            occupied += 1
        if st == "OBJECT_ONLY":
            if prev_state != "OBJECT_ONLY":
                entries += 1
                ep_first_ts = r["ts"]
            ep_obj = max(ep_obj, o)
            ep_last_ts = r["ts"]
        elif prev_state == "OBJECT_ONLY":
            close_episode()
        prev_state = st
    close_episode()

    return [entries, total, obj_max, occupied / len(rows)]

# ---------------------------------------------------------------- thong ke trong ngay (cho dashboard)
MAX_GAP_SEC = 30         # 2 ban tin cach nhau hon 30 giay thi khong tinh khoang giua la "dang o trang thai cu"


def daily_stats(rows, hog_limit_sec):
    """rows: cac ban tin cua 1 ghe tu 0h hom nay. Tra ve {"usage_pct", "hog_count"} hoac None neu chua co du lieu.
    usage_pct: % thoi gian ghe o trang thai OCCUPIED (tinh theo thoi gian, khong dem so ban tin).
    hog_count: so lan OBJECT_ONLY lien tuc cham/vuot hog_limit_sec."""
    if len(rows) < 2:
        return None
    occupied = total = 0.0
    hog = 0
    ep_max = 0
    in_ep = False
    for prev, cur in zip(rows, rows[1:]):
        dt = min((cur["ts"] - prev["ts"]) / 1000.0, MAX_GAP_SEC)
        total += dt
        if prev["state"] == "OCCUPIED":
            occupied += dt
    for r in rows:
        if r["state"] == "OBJECT_ONLY":
            in_ep = True
            ep_max = max(ep_max, r["obj_secs"] or 0)
        elif in_ep:
            hog += ep_max >= hog_limit_sec
            in_ep, ep_max = False, 0
    if in_ep:
        hog += ep_max >= hog_limit_sec
    return {"usage_pct": round(100.0 * occupied / total, 1) if total else 0.0, "hog_count": hog}

#  du lieu gia lap + mo hinh
def synth_normal(n=600, seed=RANDOM_STATE):
    """Cua so 30 phut 'binh thuong': ghe trong, ngoi hoc, hoac roi di ngan (ve sinh, lay nuoc)."""
    rng = np.random.default_rng(seed)
    X = []
    for _ in range(n):
        kind = rng.choice(["empty", "study", "break"], p=[0.30, 0.50, 0.20])
        if kind == "empty":
            X.append([0, 0, 0, 0.0])
        elif kind == "study":
            entries = int(rng.integers(0, 3))
            total = float(rng.uniform(0, 90)) if entries else 0.0
            X.append([entries, total, total / max(entries, 1) * rng.uniform(1, 1.5),
                      float(rng.uniform(0.6, 1.0))])
        else:  # roi di ngan roi quay lai, de lai do
            entries = int(rng.integers(1, 4))
            total = float(rng.uniform(30, 180))
            X.append([entries, total, min(total, float(rng.uniform(30, 150))),
                      float(rng.uniform(0.3, 0.8))])
    return np.array(X, dtype=float)


def train(seed=RANDOM_STATE):
    model = IsolationForest(n_estimators=200, contamination=0.02, random_state=seed)
    model.fit(synth_normal())
    return model


def load_or_train(path=None):
    """Co file .joblib thi nap, khong co thi huan luyen va luu lai."""
    if path is not None and path.exists():
        try:
            bundle = joblib.load(path)
            if bundle.get("features") == FEATURES:
                return bundle["model"]
        except Exception as e:                      # file hong/khac phien ban sklearn -> train lai
            log.warning("Khong nap duoc %s (%s) - huan luyen lai", path.name, e)
    model = train()
    if path is not None:
        joblib.dump({"model": model, "features": FEATURES, "trained_on": "synthetic"}, path)
        log.info("Da huan luyen IsolationForest tren du lieu gia lap, luu %s", path.name)
    return model


def predict(model, feats):
    """Tra ve (score, anomaly). score cao = bat thuong hon (score_samples cua sklearn nhan -1)."""
    X = np.array([feats], dtype=float)
    score = float(-model.score_samples(X)[0])
    anomaly = bool(model.predict(X)[0] == -1)
    return round(score, 3), anomaly


# ---------------------------------------------------------------- chay dinh ky tren gateway
def evaluate(store, model, window_sec, now_ms=None):
    """Tinh ket qua cho moi ghe trong DB. Tra ve dict seat -> {score, anomaly, feats}."""
    now_ms = now_ms or int(time.time() * 1000)
    out = {}
    for seat in store.seats():
        feats = window_features(store.readings_since(seat, now_ms - window_sec * 1000))
        if feats is None:
            continue
        score, anomaly = predict(model, feats)
        out[seat] = {"score": score, "anomaly": anomaly, "feats": feats}
    return out

def run_stats(gw):
    """Thong ke ngay (tu 0h hom nay) cho tung ghe, gui len CoreIOT cho dashboard."""
    import config
    midnight = time.mktime(time.localtime()[:3] + (0, 0, 0, 0, 0, -1))
    for seat in gw.store.seats():
        st = daily_stats(gw.store.readings_since(seat, int(midnight * 1000)), config.HOG_LIMIT_SEC)
        if st is None:
            continue
        gw.stats[seat] = st
        gw.tb.send_telemetry(seat, st)
        log.info("%s hom nay: su dung %.1f%%, bi giu cho %d lan", seat, st["usage_pct"], st["hog_count"])

def run_once(gw, model):
    import config
    run_stats(gw)
    results = evaluate(gw.store, model, config.AI_WINDOW_SEC)
    for seat, r in results.items():
        gw.hog[seat] = r
        gw.tb.send_telemetry(seat, {"hog_score": r["score"], "hog_anomaly": r["anomaly"]})
        log.info("%s feats=%s score=%.3f anomaly=%s", seat, [round(x, 1) for x in r["feats"]], r["score"], r["anomaly"])
    if results:
        gw.tb.send_telemetry(config.ROOM_DEVICE, {
            "hog_score": max(r["score"] for r in results.values()),
            "hog_anomaly": any(r["anomaly"] for r in results.values()),
        })
    return results


def loop(gw):
    """Thread nen: moi AI_INTERVAL_SEC chay 1 lan. Loi khong lam sap gateway."""
    import config
    model = load_or_train(config.AI_MODEL_PATH)
    log.info("AI job chay moi %d giay, cua so %d giay", config.AI_INTERVAL_SEC, config.AI_WINDOW_SEC)
    while True:
        time.sleep(config.AI_INTERVAL_SEC)
        try:
            run_once(gw, model)
        except Exception:
            log.exception("AI job loi (bo qua, thu lai o lan sau)")


# ---------------------------------------------------------------- chay tay
def _demo():
    model = train()
    cases = {
        "Ghe trong (khong ai)":                       [0, 0, 0, 0.0],
        "Ngoi hoc binh thuong":                       [1, 40, 40, 0.9],
        "Di ve sinh 2 phut roi quay lai":             [1, 120, 120, 0.5],
        "De balo 20 phut roi di (GIU CHO)":           [1, 1200, 1200, 0.1],
        "De balo ca cua so 30 phut (GIU CHO)":        [1, 1800, 1800, 0.0],
        "Seat-01 cua fake_bridge (6 dot x 180 giay)": [6, 1080, 180, 0.2],
        "Trang thai nhap nhay lien tuc":              [12, 600, 60, 0.3],
    }
    print(f"{'Tinh huong':<46}{'features':<28}{'score':>7}  anomaly")
    for name, feats in cases.items():
        score, anomaly = predict(model, feats)
        print(f"{name:<46}{str([round(x, 1) for x in feats]):<28}{score:>7}  {anomaly}")
    X = synth_normal(2000, seed=7)                 # tap kiem tra rieng, khac hat giong
    fp = float(np.mean(model.predict(X) == -1))
    print(f"\nBao dong nham tren 2000 cua so binh thuong gia lap moi: {fp*100:.1f}%")


def _once():
    import config
    from store import Store
    store = Store(config.DB_PATH)
    model = load_or_train(config.AI_MODEL_PATH)
    res = evaluate(store, model, config.AI_WINDOW_SEC)
    if not res:
        print("Chua du du lieu trong gateway.db (can >= 6 ban tin moi ghe trong cua so).")
    for seat, r in res.items():
        print(f"{seat}: feats={[round(x, 1) for x in r['feats']]} score={r['score']} anomaly={r['anomaly']}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--demo", action="store_true", help="thu mo hinh tren cac tinh huong mau")
    g.add_argument("--once", action="store_true", help="danh gia du lieu that trong gateway.db")
    g.add_argument("--retrain", action="store_true", help="xoa mo hinh cu va huan luyen lai")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)-6s %(message)s", datefmt="%H:%M:%S")
    if args.demo:
        _demo()
    elif args.once:
        _once()
    else:
        import config
        config.AI_MODEL_PATH.unlink(missing_ok=True)
        load_or_train(config.AI_MODEL_PATH)
