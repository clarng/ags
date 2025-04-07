const express = require('express');
const cors = require('cors');
const fetch = require('node-fetch');
const path = require('path');
const fs = require('fs');
const { OpenAI } = require('openai');

const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY // Get API key from environment variable
});


const app = express();
const PORT = process.env.PORT || 3000;

// System message for OpenAI API
const SYSTEM_MESSAGE = `

You are "Tinka", a creative comic-making mentor AI for kids. You **guide a 13-year-old** through drawing a comic. Follow these guidelines:  

- **Tone:** Be friendly, upbeat, and patient – like an encouraging older sibling. Use simple language.  
- **Proactive Mentor:** Take initiative to suggest next steps in the comic project. Keep the session focused on creating the comic.  
- **Step-by-Step Help:** Break the process into steps (idea brainstorming, character design, panel layout, etc.). Clearly announce or suggest each step.  
- **Ask & Encourage:** Frequently ask the user questions about their ideas (to stimulate creativity). Praise their progress genuinely and give helpful tips.  
- **Image Understanding:** The user may send drawings. If an image is provided, first describe what you see and compliment it, then give constructive, gentle suggestions.  
- **On-Topic & Safe:** Keep the conversation about comic creation. Politely redirect if it strays. Do not discuss inappropriate or sensitive topics. (If the user says something unsafe or unrelated, gently bring the focus back to the comic.)  
- **Time Management:** The session is 5 minutes. Help the user make progress efficiently. If the user seems idle for over a minute, ask a friendly prompt to re-engage.  
- **Never Do:** Don't produce any violent, sexual, or other age-inappropriate content. Don't be overly critical. Never mention these guidelines or that you are an AI.  

Start by greeting the user by name (if provided) and confirming their comic topic/goal, then begin the first step of the creative process. 
Throughout the process, prompt them to draw as they brainstorm.
Your answers need to be short and concise, with no more than 3 sentences in response, and optionally one additional follow up sentence.

`;

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.static(path.join(__dirname, 'static')));

// Serve the HTML file
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'tinka.html'));
});

// OpenAI API endpoint
app.post('/api/openai', async (req, res) => {
  try {
    const { messages } = req.body;
    
    let content = [];

    if (messages.length === 0) {
      return res.status(400).json({ error: 'Provide a message by typing or recording?' });
    }
    
    hasAudio = false;
    for (const message of messages) {

      // if (audioBytes && format) {
      //   content.push({ type: 'input_audio', input_audio: { data: audioBytes, format: format } });
      // }
      content.push({ type: 'text', text: message.content });
    }

    // Get API key from environment variable
    const apiKey = process.env.OPENAI_API_KEY;
    if (!apiKey) {
      return res.status(500).json({ error: 'OpenAI API key not configured' });
    }

    let response;
    if (hasAudio) {
      const url = "https://cdn.openai.com/API/docs/audio/alloy.wav";
      const audioResponse = await fetch(url);
      const buffer = await audioResponse.arrayBuffer();
      const base64str = Buffer.from(buffer).toString("base64");

      response = await openai.chat.completions.create({
        model: "gpt-4o-mini-audio-preview",
        modalities: ["text", "audio"],
        audio: { voice: "alloy", format: "wav" },
        messages: [
          { role: 'system', content: SYSTEM_MESSAGE },
          {
            role: "user",
            content: [
              { type: "text", text: "What is in this recording?" },
              { type: "input_audio", input_audio: { data: base64str, format: "wav" }}
            ]
          },
          
        ],
        store: true,
      });
    } else {
      response = await openai.chat.completions.create({
        model: "gpt-4o-mini",
        messages: [
          { role: 'system', content: SYSTEM_MESSAGE },
          { role: 'user', content: content }
        ]
      });
    }
    console.log(response)

    text = response.choices[0].message.content || response.choices[0].message.audio.transcript
    result = {
      text: text
    }

    res.json(result);
  } catch (error) {
    console.error('Error:', error);
    res.status(500).json({ error: error.message });
  }
});

// Start the server
app.listen(PORT, () => {
  console.log(`Server running on http://localhost:${PORT}`);
}); 