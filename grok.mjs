const apiKey = process.env.XAPI || process.env.XAI_API_KEY;
if (!apiKey) {
  console.error("ERROR: XAPI/XAI_API_KEY not set. Run: export XAPI=xai-...");
  process.exit(1);
}

const model = process.argv[2] || "grok-4";
const prompt = process.argv.slice(3).join(" ") || "Say hello in one sentence.";

const res = await fetch("https://api.x.ai/v1/chat/completions", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    Authorization: `Bearer ${apiKey}`,
  },
  body: JSON.stringify({
    model,
    messages: [{ role: "user", content: prompt }],
  }),
});

if (!res.ok) {
  console.error(`Error ${res.status}: ${await res.text()}`);
  process.exit(1);
}

const data = await res.json();
console.log(data.choices[0].message.content);