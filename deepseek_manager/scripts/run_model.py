import argparse
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

def main():
    parser = argparse.ArgumentParser(description="Run DeepSeek models")
    parser.add_argument("--model", default="deepseek-ai_deepseek-coder-1.3b-instruct",
                      help="Model directory name")
    parser.add_argument("--quant", choices=["4bit", "8bit", "none"], default="none",
                      help="Quantization method")
    parser.add_argument("--max-tokens", type=int, default=200,
                      help="Maximum tokens to generate")
    parser.add_argument("--temperature", type=float, default=0.7,
                      help="Sampling temperature")
    
    args = parser.parse_args()
    model_path = f"deepseek_storage/extracted/{args.model}"
    
    # Load model with quantization
    load_kwargs = {
        "device_map": "auto",
        "trust_remote_code": True
    }
    
    if args.quant == "4bit":
        load_kwargs.update({
            "load_in_4bit": True,
            "bnb_4bit_compute_dtype": torch.float16
        })
    elif args.quant == "8bit":
        load_kwargs["load_in_8bit"] = True
    
    model = AutoModelForCausalLM.from_pretrained(model_path, **load_kwargs)
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    
    # Simple chat interface
    while True:
        prompt = input("\nUser: ")
        if prompt.lower() in ["exit", "quit"]:
            break
            
        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
        outputs = model.generate(
            **inputs,
            max_new_tokens=args.max_tokens,
            temperature=args.temperature,
            do_sample=True
        )
        
        response = tokenizer.decode(outputs[0], skip_special_tokens=True)
        print(f"\nAssistant: {response}")

if __name__ == "__main__":
    main() 