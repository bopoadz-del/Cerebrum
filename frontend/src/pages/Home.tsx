import { ChatInterface } from '@/components/ChatInterface';
import { useState } from 'react';
import type { Message, Attachment } from '@/types';

export default function Home() {
  const [messages] = useState<Message[]>([]);
  
  const handleSendMessage = (content: string, attachments?: Attachment[]) => {
    // Handle message sending
    console.log('Message:', content, 'Attachments:', attachments);
  };
  
  return <ChatInterface messages={messages} onSendMessage={handleSendMessage} />;
}
