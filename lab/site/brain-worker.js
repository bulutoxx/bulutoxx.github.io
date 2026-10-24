// 🧠 Akıllı mod: açık kaynak dil modeli ayrı iş parçacığında çalışır (ekran donmaz). Kaynak: github.com/mlc-ai/web-llm (Apache 2.0)
import { WebWorkerMLCEngineHandler } from "https://cdn.jsdelivr.net/npm/@mlc-ai/web-llm@0.2.85/+esm";
const handler = new WebWorkerMLCEngineHandler();
self.onmessage = (msg) => handler.onmessage(msg);
