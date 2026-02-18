import { motion } from 'framer-motion';
import { HelpCircle, Book, MessageSquare, Video, Mail, ExternalLink } from 'lucide-react';
import { ModuleHeader } from '@/components/ModuleHeader';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

const resources = [
  {
    icon: Book,
    title: 'Documentation',
    description: 'Comprehensive guides and API reference',
    action: 'View Docs',
    color: 'indigo',
  },
  {
    icon: Video,
    title: 'Video Tutorials',
    description: 'Learn with step-by-step video guides',
    action: 'Watch Videos',
    color: 'red',
  },
  {
    icon: MessageSquare,
    title: 'Community Forum',
    description: 'Connect with other users',
    action: 'Join Forum',
    color: 'emerald',
  },
  {
    icon: Mail,
    title: 'Contact Support',
    description: 'Get help from our support team',
    action: 'Contact Us',
    color: 'amber',
  },
];

const faqs = [
  {
    question: 'What file formats are supported?',
    answer: 'We support a wide range of formats including PDF, DOCX, XLSX, CSV, JSON, DWG, IFC, MP3, WAV, and many more. Each analysis module has its own supported formats listed on the upload page.',
  },
  {
    question: 'How secure is my data?',
    answer: 'All data is encrypted in transit and at rest. We use industry-standard security practices and comply with SOC 2 Type II. Your files are automatically deleted after analysis unless you choose to save them.',
  },
  {
    question: 'Can I use the API?',
    answer: 'Yes! We offer a comprehensive REST API for all analysis modules. You can generate API keys in your settings and find the full documentation in our API reference.',
  },
  {
    question: 'What is the maximum file size?',
    answer: 'File size limits vary by module. Most support files up to 50MB, with some supporting up to 500MB for archives. Contact us if you need to process larger files.',
  },
];

export default function HelpPage() {
  return (
    <div className="p-8">
      <ModuleHeader
        title="Help & Support"
        description="Find answers and get help with Reasoner"
        icon={HelpCircle}
        iconColor="gray"
      />

      {/* Resources Grid */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8"
      >
        {resources.map((resource, index) => (
          <Card key={index} className="card-hover">
            <CardContent className="p-6">
              <div className={`w-12 h-12 rounded-lg bg-${resource.color}-50 flex items-center justify-center mb-4`}>
                <resource.icon className={`w-6 h-6 text-${resource.color}-600`} />
              </div>
              <h3 className="font-semibold text-gray-900 mb-1">{resource.title}</h3>
              <p className="text-sm text-gray-500 mb-4">{resource.description}</p>
              <Button variant="outline" size="sm" className="w-full">
                {resource.action}
                <ExternalLink className="w-3 h-3 ml-1" />
              </Button>
            </CardContent>
          </Card>
        ))}
      </motion.div>

      {/* FAQ Section */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
      >
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Frequently Asked Questions</h2>
        <div className="space-y-4">
          {faqs.map((faq, index) => (
            <Card key={index}>
              <CardHeader>
                <CardTitle className="text-base">{faq.question}</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-gray-600">{faq.answer}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      </motion.div>
    </div>
  );
}
