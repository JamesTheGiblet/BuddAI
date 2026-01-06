import json
import http.client
import socket
from typing import List, Dict, Union, Generator, Optional
from core.buddai_shared import MODELS, OLLAMA_POOL, OLLAMA_HOST, OLLAMA_PORT

class OllamaClient:
    """Handles communication with the local Ollama instance"""

    def query(self, model_key: str, messages: List[Dict], stream: bool = False, options: Dict = None) -> Union[str, Generator[str, None, None]]:
        """Send a chat request to Ollama"""
        model_name = MODELS.get(model_key, model_key) # Handle key or direct name
        
        default_options = {
            "temperature": 0.0,
            "top_p": 1.0,
            "top_k": 1,
            "num_ctx": 1024
        }
        if options:
            default_options.update(options)

        body = {
            "model": model_name,
            "messages": messages,
            "stream": stream,
            "options": default_options
        }
        
        headers = {"Content-Type": "application/json"}
        json_body = json.dumps(body)
        
        # Retry logic for connection stability
        for attempt in range(3):
            conn = None
            try:
                # Re-serialize in case of modification (CPU fallback)
                json_body = json.dumps(body)
                
                conn = OLLAMA_POOL.get_connection()
                conn.request("POST", "/api/chat", json_body, headers)
                response = conn.getresponse()
                
                if stream:
                    if response.status != 200:
                        error_text = response.read().decode('utf-8')
                        conn.close()
                        
                        # GPU OOM Detection -> CPU Fallback
                        if "CUDA" in error_text or "buffer" in error_text:
                            if "num_gpu" not in body["options"]:
                                print("⚠️ GPU OOM detected. Switching to CPU mode...")
                                body["options"]["num_gpu"] = 0 # Force CPU
                                continue

                        try:
                            err_msg = f"Error {response.status}: {json.loads(error_text).get('error', error_text)}"
                        except:
                            err_msg = f"Error {response.status}: {error_text}"
                        
                        if "num_gpu" in body["options"]:
                            err_msg += "\n\n(⚠️ CPU Mode also failed. System RAM might be full.)"
                        elif "CUDA" in err_msg or "buffer" in err_msg:
                            err_msg += "\n\n(⚠️ GPU Out of Memory. Retrying on CPU failed.)"
                            
                        return (x for x in [err_msg])

                    return self._stream_response(response, conn)
                
                if response.status == 200:
                    data = json.loads(response.read().decode('utf-8'))
                    OLLAMA_POOL.return_connection(conn)
                    return data.get("message", {}).get("content", "No response")
                else:
                    error_text = response.read().decode('utf-8')
                    conn.close()
                    
                    if "CUDA" in error_text or "buffer" in error_text:
                        if "num_gpu" not in body["options"]:
                            print("⚠️ GPU OOM detected. Switching to CPU mode...")
                            body["options"]["num_gpu"] = 0
                            continue

                    return f"Error {response.status}: {error_text}"
                        
            except (http.client.NotConnected, BrokenPipeError, ConnectionResetError, socket.timeout) as e:
                if conn: conn.close()
                if attempt == 2:
                    return f"Error: Connection failed. {str(e)}"
                continue
            except Exception as e:
                if conn: conn.close()
                return f"Error: {str(e)}"
                
    def _stream_response(self, response, conn) -> Generator[str, None, None]:
        """Yield chunks from HTTP response"""
        fully_consumed = False
        has_content = False
        try:
            while True:
                line = response.readline()
                if not line: break
                try:
                    data = json.loads(line.decode('utf-8'))
                    if "message" in data:
                        content = data["message"].get("content", "")
                        if content: 
                            has_content = True
                            yield content
                    if data.get("done"): 
                        fully_consumed = True
                        break
                except: pass
        except Exception as e:
            yield f"\n[Stream Error: {str(e)}]"
        finally:
            if fully_consumed:
                OLLAMA_POOL.return_connection(conn)
            else:
                conn.close()
        
        if not has_content and not fully_consumed:
            yield "\n[Error: Empty response from Ollama. Check if model is loaded.]"

    def reset_gpu(self) -> str:
        """Force unload models from GPU to free VRAM"""
        try:
            conn = http.client.HTTPConnection(OLLAMA_HOST, OLLAMA_PORT, timeout=10)
            for model in MODELS.values():
                body = json.dumps({"model": model, "keep_alive": 0})
                conn.request("POST", "/api/generate", body)
                resp = conn.getresponse()
                resp.read()
            conn.close()
            return "✅ GPU Memory Cleared (Models Unloaded)"
        except Exception as e:
            return f"❌ Error clearing GPU: {str(e)}"