import jev
import llm_only

import kit

kit.run_benchmark("12 · Benchmark — every message, both pipelines", jev=jev.run, llm=llm_only.run)
