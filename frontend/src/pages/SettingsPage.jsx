import { useEffect, useState } from 'react';
import { toast } from 'sonner';

import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { api } from '../lib/api';

export default function SettingsPage() {
  const [providers, setProviders] = useState([]);

  const loadProviders = () => api.get('/providers').then(setProviders).catch((error) => toast.error(error.message));

  useEffect(() => {
    loadProviders();
  }, []);

  const updateField = (providerName, key, value) => {
    setProviders((current) => current.map((provider) => (provider.provider === providerName ? { ...provider, [key]: value } : provider)));
  };

  const handleSave = async (provider) => {
    try {
      await api.put(`/providers/${provider.provider}`, provider);
      toast.success(`${provider.label} settings saved`);
      loadProviders();
    } catch (error) {
      toast.error(error.message);
    }
  };

  return (
    <div className="stack" data-testid="settings-page">
      <header className="page-header">
        <div>
          <div className="eyebrow">Model Plane</div>
          <h1 className="page-title" data-testid="settings-page-title">Choose which provider drafts and reviews your outputs</h1>
          <p className="page-subtitle" data-testid="settings-page-subtitle">OpenAI and Anthropic can use the universal key. OpenRouter and MiniMax stay available for your custom API keys and base URLs.</p>
        </div>
      </header>

      <section className="grid-2">
        {providers.map((provider) => (
          <article key={provider.provider} className="form-shell" data-testid={`provider-card-${provider.provider}`}>
            <div className="panel-header">
              <div>
                <div className="eyebrow">{provider.status}</div>
                <h2 className="panel-title" data-testid={`provider-title-${provider.provider}`}>{provider.label}</h2>
              </div>
              <Button onClick={() => handleSave(provider)} variant={provider.auth_mode === 'custom' ? 'danger' : 'primary'} data-testid={`provider-save-${provider.provider}`}>Save</Button>
            </div>
            <div className="field-stack"><label className="field-label">Model</label><Input value={provider.model} onChange={(e) => updateField(provider.provider, 'model', e.target.value)} data-testid={`provider-model-${provider.provider}`} /></div>
            <div className="field-stack"><label className="field-label">Auth mode</label><select className="select" value={provider.auth_mode} onChange={(e) => updateField(provider.provider, 'auth_mode', e.target.value)} data-testid={`provider-auth-mode-${provider.provider}`}><option value="universal">Universal</option><option value="custom">Custom</option></select></div>
            <div className="field-stack"><label className="field-label">Base URL</label><Input value={provider.base_url || ''} onChange={(e) => updateField(provider.provider, 'base_url', e.target.value)} data-testid={`provider-base-url-${provider.provider}`} /></div>
            <div className="field-stack"><label className="field-label">Custom API key</label><Input type="password" placeholder={provider.key_last4 ? `Stored ending ${provider.key_last4}` : 'Optional unless provider requires custom auth'} onChange={(e) => updateField(provider.provider, 'custom_api_key', e.target.value)} data-testid={`provider-api-key-${provider.provider}`} /></div>
            <div className="field-stack"><label className="field-label">Enabled</label><label data-testid={`provider-enabled-${provider.provider}`}><input type="checkbox" checked={provider.enabled} onChange={(e) => updateField(provider.provider, 'enabled', e.target.checked)} /> Active for analysis requests</label></div>
          </article>
        ))}
      </section>
    </div>
  );
}
