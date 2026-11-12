"""Poll HyP3 until every submitted site's jobs are finished, then collect each site (resilient to URS hiccups)."""
import json, time
from pathlib import Path
from drishti.insar import hyp3, collect, OUT

def main(poll_s=300, max_hours=6):
    sites = sorted(p.name.split("_")[0] for p in OUT.glob("*_jobs.json"))
    pending = [s for s in sites if not (OUT / f"{s}.json").exists()]
    t0 = time.time()
    while pending and time.time() - t0 < max_hours * 3600:
        try:
            h = hyp3()
            for s in list(pending):
                jobs = h.find_jobs(name=f"drishti-{s}")
                st = [j.status_code for j in jobs]
                if st and all(x in ("SUCCEEDED", "FAILED") for x in st):
                    collect(s)
                    pending.remove(s)
                else:
                    print(s, {k: st.count(k) for k in set(st)}, flush=True)
        except Exception as e:
            print("poll error:", repr(e)[:120], flush=True)
        if pending:
            time.sleep(poll_s)
    print("done; pending:", pending)

if __name__ == "__main__":
    main()
