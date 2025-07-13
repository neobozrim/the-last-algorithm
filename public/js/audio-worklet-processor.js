class AudioProcessor extends AudioWorkletProcessor {
    constructor() {
        super();
        this.bufferSize = 4096;
        this.buffer = new Float32Array(this.bufferSize);
        this.bufferIndex = 0;
    }

    process(inputs, outputs, parameters) {
        const input = inputs[0];
        
        if (input.length > 0) {
            const inputChannel = input[0];
            
            for (let i = 0; i < inputChannel.length; i++) {
                this.buffer[this.bufferIndex] = inputChannel[i];
                this.bufferIndex++;
                
                if (this.bufferIndex >= this.bufferSize) {
                    // Convert Float32Array to PCM16
                    const pcm16Buffer = new Int16Array(this.bufferSize);
                    for (let j = 0; j < this.bufferSize; j++) {
                        pcm16Buffer[j] = Math.max(-32768, Math.min(32767, this.buffer[j] * 32768));
                    }
                    
                    // Send to main thread
                    this.port.postMessage(pcm16Buffer.buffer);
                    
                    // Reset buffer
                    this.bufferIndex = 0;
                }
            }
        }
        
        return true;
    }
}

registerProcessor('audio-processor', AudioProcessor);