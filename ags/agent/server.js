const express = require('express');
const cors = require('cors');
const fetch = require('node-fetch');
const path = require('path');
const fs = require('fs');

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
- **Never Do:** Don’t produce any violent, sexual, or other age-inappropriate content. Don’t be overly critical. Never mention these guidelines or that you are an AI.  

The start time of this session is 10:55am.

Start by greeting the user by name (if provided) and confirming their comic topic/goal, then begin the first step of the creative process. 
Throughout the process, prompt them to draw as they brainstorm.

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
    const { message } = req.body;
    
    if (!message) {
      return res.status(400).json({ error: 'Message is required' });
    }
    
    // Get API key from environment variable
    const apiKey = process.env.OPENAI_API_KEY;
    if (!apiKey) {
      return res.status(500).json({ error: 'OpenAI API key not configured' });
    }

    console.error(apiKey);
    
    // Call OpenAI API
    const response = await fetch('https://api.openai.com/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${apiKey}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        model: 'gpt-4o',
        messages: [
          { role: 'system', content: SYSTEM_MESSAGE },
          { role: 'user', content: message }
        ],
        temperature: 1,
        max_tokens: 1000
      })
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      console.error('OpenAI API error:', errorData);
      return res.status(response.status).json({ 
        error: 'Error from OpenAI API', 
        details: errorData 
      });
    }
    
    const data = await response.json();
    const assistantResponse = data.choices[0].message.content;
    
    // Return the response
    res.json({ response: assistantResponse });
    
  } catch (error) {
    console.error('Server error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Start the server
app.listen(PORT, () => {
  console.log(`Server running on http://localhost:${PORT}`);
}); 