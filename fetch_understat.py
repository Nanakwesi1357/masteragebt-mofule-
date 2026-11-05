"""Optional: pull xG results from Understat (top-5 leagues only).

Needs:  pip install understat aiohttp
Understat has no official API and its site changes, so this step is best-effort:
if it fails, the pipeline still runs with shots-based features only.
"""
import asyncio
import json
from datetime import date

from common import RAW, UNDERSTAT


async def _run(years):
    import aiohttp
    from understat import Understat

    async with aiohttp.ClientSession() as session:
        u = Understat(session)
        for slug in UNDERSTAT.values():
            for y in years:
                try:
                    res = await u.get_league_results(slug, y)
                    d = RAW / "understat"
                    d.mkdir(parents=True, exist_ok=True)
                    (d / f"{slug}_{y}.json").write_text(json.dumps(res))
                    print(f"  understat {slug} {y}: {len(res)} matches")
                except Exception as e:  # noqa: BLE001
                    print(f"  understat {slug} {y} FAILED: {str(e)[:100]}")


def main(n_seasons=5):
    today = date.today()
    start = today.year if today.month >= 7 else today.year - 1
    years = list(range(start - n_seasons + 1, start + 1))
    try:
        asyncio.run(_run(years))
        return True
    except ImportError:
        print("understat/aiohttp not installed: skipping xG (pip install understat aiohttp)")
        return False


if __name__ == "__main__":
    main()
