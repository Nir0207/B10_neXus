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
    expect(mockedIntelligenceService.query).toHaveBeenCalled();
    expect(await screen.findByText('EGFR has pathway-linked leads.')).toBeTruthy();
  });
});
