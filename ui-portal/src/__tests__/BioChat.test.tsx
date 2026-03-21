import React from 'react';
import '@testing-library/jest-dom';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import BioChat from '@/components/BioChat';
import { intelligenceService } from '@/services/intelligenceService';

jest.mock('@/services/intelligenceService', () => ({
  intelligenceService: {
    query: jest.fn(),
  },
}));

const mockedIntelligenceService = intelligenceService as jest.Mocked<typeof intelligenceService>;

describe('BioChat', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders chat interface correctly', () => {
    render(<BioChat organType="liver" />);
    expect(screen.getByText('Bio-Chat Assistant')).toBeTruthy();
    expect(screen.getByPlaceholderText('Ask Bio-Chat...')).toBeTruthy();
    expect(screen.getByText('What is CYP3A4?')).toBeTruthy();
  });

  it('sends a query and clears input upon form submission', async () => {
    mockedIntelligenceService.query.mockResolvedValue({
      mode: 'drug_leads',
      reply: 'EGFR has pathway-linked leads.',
      resolved_entity: 'EGFR',
      sources: ['Source: UniProt'],
    });

    render(
      <BioChat
        organType="liver"
        data={{
          nodes: [{ id: 'gene1', label: 'EGFR', type: 'Gene', properties: { uniprot_id: 'P00533' } }],
          edges: [],
        }}
      />
    );
    const input = screen.getByPlaceholderText('Ask Bio-Chat...') as HTMLInputElement;
    fireEvent.change(input, { target: { value: 'What is CYP3A4?' } });
    expect(input.value).toBe('What is CYP3A4?');

    const button = screen.getByRole('button', { name: /send/i });
    fireEvent.click(button);

    await waitFor(() => {
      expect(input.value).toBe('');
    });
    expect(mockedIntelligenceService.query).toHaveBeenCalledWith(
      expect.objectContaining({
        prompt: 'What is CYP3A4?',
        history: expect.arrayContaining([
          expect.objectContaining({ role: 'assistant' }),
          expect.objectContaining({ role: 'user', text: 'What is CYP3A4?' }),
        ]),
      }),
      expect.any(Object),
    );
    expect(await screen.findByText('EGFR has pathway-linked leads.')).toBeTruthy();
  });

  it('renders an inline chart when the intelligence service returns a visual payload', async () => {
    mockedIntelligenceService.query.mockResolvedValue({
      mode: 'visual_report',
      reply: 'Visual summary',
      resolved_entity: 'alzheimers-disease',
      sources: ['Source: Discovery Graph'],
      visual_payload: {
        chart_type: 'bar',
        title: "Alzheimer's disease Gene Distribution",
        disease_id: 'alzheimers-disease',
        disease_name: "Alzheimer's disease",
        x_key: 'gene_symbol',
        y_key: 'association_score',
        datasets: [{ gene_symbol: 'APP', association_score: 0.91 }],
        clinical_summary: 'Visual summary',
      },
    });

    render(<BioChat organType="brain" />);

    const input = screen.getByPlaceholderText('Ask Bio-Chat...');
    fireEvent.change(input, { target: { value: "Analyze the rise of Alzheimer's genes" } });
    fireEvent.click(screen.getByRole('button', { name: /send/i }));

    expect(await screen.findByText("Alzheimer's disease Gene Distribution")).toBeTruthy();
    expect(await screen.findByText('Visual summary')).toBeTruthy();
  });
});
