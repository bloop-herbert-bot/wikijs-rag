/**
 * wikijs-search OpenClaw Plugin
 * 
 * Provides semantic search across Wiki.js documentation using RAG.
 * Requires RAG API running on http://localhost:8765
 */

import { Type } from "@sinclair/typebox";

const RAG_API_URL = process.env.RAG_API_URL || 'http://localhost:8765';

/**
 * Query Wiki.js documentation via RAG API
 */
async function queryWikiJS(query, topK = 3, filterPath = null) {
  const requestBody = {
    query: query.trim(),
    top_k: topK
  };

  if (filterPath) {
    requestBody.filter_path = filterPath;
  }

  try {
    const response = await fetch(`${RAG_API_URL}/query`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(requestBody),
      signal: AbortSignal.timeout(10000)
    });

    if (!response.ok) {
      if (response.status === 503) {
        throw new Error('RAG API not initialized. ChromaDB may be empty.');
      }
      throw new Error(`RAG API error: ${response.status} ${response.statusText}`);
    }

    const data = await response.json();
    return data;
  } catch (error) {
    if (error.name === 'AbortError') {
      throw new Error('RAG API timeout after 10 seconds');
    }
    if (error.cause?.code === 'ECONNREFUSED') {
      throw new Error(`RAG API not reachable at ${RAG_API_URL}. Is the service running?`);
    }
    throw error;
  }
}

/**
 * Format search results for LLM consumption
 */
function formatResults(data) {
  if (!data.results || data.results.length === 0) {
    return {
      type: "text",
      text: `No results found for query: "${data.query}"\n\nThe Wiki.js documentation does not contain information about this topic.`
    };
  }

  let output = `Found ${data.count} relevant documentation pages for: "${data.query}"\n\n`;

  data.results.forEach((result, i) => {
    const score = parseFloat(result.score).toFixed(2);
    const title = result.metadata?.title || 'Unknown';
    const path = result.metadata?.path || 'Unknown';
    
    output += `## Result ${i + 1}: ${title} (relevance: ${score})\n`;
    output += `**Source:** ${path}\n\n`;
    output += `${result.content}\n\n`;
    
    if (result.metadata?.description) {
      output += `_Description: ${result.metadata.description}_\n\n`;
    }
    
    output += `---\n\n`;
  });

  output += `\n**Note:** Always cite the source path when using information from these results.`;

  return {
    type: "text",
    text: output
  };
}

export default function (api) {
  api.registerTool({
    name: "wikijs_search",
    description: "Semantic search across Wiki.js documentation (Smart Home, Network, Infrastructure, Containers). Use this before saying 'I don't know' about technical setup questions.",
    parameters: Type.Object({
      query: Type.String({
        description: "Natural language search query (e.g., 'ioBroker IP address', 'How to configure Shelly devices?')"
      }),
      top_k: Type.Optional(Type.Number({
        description: "Number of results to return (default: 3, max: 10)",
        minimum: 1,
        maximum: 10,
        default: 3
      })),
      filter_path: Type.Optional(Type.String({
        description: "Optional path filter (e.g., 'Container/', 'Netzwerk/')"
      }))
    }),
    async execute(_id, params) {
      try {
        // Validate query
        if (!params.query || params.query.trim() === '') {
          return {
            content: [{
              type: "text",
              text: "Error: Query cannot be empty."
            }]
          };
        }

        // Execute search
        const topK = params.top_k || 3;
        const data = await queryWikiJS(params.query, topK, params.filter_path);
        
        // Format results
        const formatted = formatResults(data);
        
        return { content: [formatted] };
      } catch (error) {
        return {
          content: [{
            type: "text",
            text: `Error searching Wiki.js: ${error.message}\n\nMake sure the RAG API is running:\n\`\`\`bash\ncd ~/.openclaw/workspace-githerbert/wikijs-rag\nuvicorn rag_api:app --host 0.0.0.0 --port 8765\n\`\`\``
          }]
        };
      }
    }
  });

  // Register health check tool (optional, for debugging)
  api.registerTool(
    {
      name: "wikijs_health",
      description: "Check if Wiki.js RAG API is running and healthy",
      parameters: Type.Object({}),
      async execute(_id, _params) {
        try {
          const response = await fetch(`${RAG_API_URL}/health`, {
            signal: AbortSignal.timeout(5000)
          });

          if (!response.ok) {
            throw new Error(`API returned ${response.status}`);
          }

          const health = await response.json();
          
          return {
            content: [{
              type: "text",
              text: `✅ Wiki.js RAG API is healthy\n\n` +
                    `**Status:** ${health.status}\n` +
                    `**Collection:** ${health.collection}\n` +
                    `**Documents:** ${health.documents}\n` +
                    `**Ollama:** ${health.ollama}`
            }]
          };
        } catch (error) {
          return {
            content: [{
              type: "text",
              text: `❌ Wiki.js RAG API is not available\n\n` +
                    `**Error:** ${error.message}\n` +
                    `**URL:** ${RAG_API_URL}\n\n` +
                    `Make sure the service is running.`
            }]
          };
        }
      }
    },
    { optional: true } // Health check is opt-in
  );
}
