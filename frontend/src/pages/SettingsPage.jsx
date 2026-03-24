import { useEffect, useState } from 'react';
import { toast } from 'sonner';

import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { api } from '../lib/api';

export default function SettingsPage() {
  const [providers, setProviders] = useState([]);
  const [savingProvider, setSavingProvider] = useState('');
  const [removingProvider, setRemovingProvider] = useState('');

  const loadProviders = () => api.get('/providers').then(setProviders).catch((error) => toast.error(error.message));

  useEffect(() => {
    loadProviders();
  }, []);

  const updateField = (providerName, key, value) => {
    setProviders((current) => current.map((provider) => (provider.provider === providerName ? { ...provider, [key]: value } : provider)));
  };

  const handleSave = async (provider) => {
    try {
      setSavingProvider(provider.provider);
      await api.put(`/providers/${provider.provider}`, provider);
      toast.success(`${provider.label} settings saved`);
      loadProviders();
    } catch (error) {
      toast.error(error.message);
    } finally {
      setSavingProvider('');
    }
  };

  const handleRemoveKey = async (provider) => {
    try {
      setRemovingProvider(provider.provider);
      await api.delete(`/providers/${provider.provider}/custom-key`);
      toast.success(`${provider.label} custom key removed`);
      loadProviders();
    } catch (error) {
      toast.error(error.message);
    } finally {
      setRemovingProvider('');
    }
  };

  return (
    <div className="stack" data-testid="settings-page">
      <header className="page-header">
        <div>
          <div className="eyebrow">Model Plane</div>
          <h1 className="page-title" data-testid="settings-page-title">Choose which provider drafts and reviews your outputs</h1>
          <p className="page-subtitle" data-testid="settings-page-subtitle">OpenAI and Anthropic can use the universal key. OpenRouter and MiniMax stay available for your custom API keys, which are now stored encrypted and can be removed at any time.</p>
        </div>
      </header>

      <section className="grid-2">
        {providers.map((provider) => (
          <article key={provider.provider} className="form-shell" data-testid={`provider-card-${provider.provider}`}>
            <div className="panel-header">
              <div>
                <div className="eyebrow" data-testid={`provider-status-${provider.provider}`}>{provider.status}</div>
                <h2 className="panel-title" data-testid={`provider-title-${provider.provider}`}>{provider.label}</h2>
                <p className="panel-copy" data-testid={`provider-key-storage-${provider.provider}`}>
                  {provider.has_custom_key ? `Encrypted custom key stored ending ${provider.key_last4}. Save a new value below to replace it.` : 'No custom key stored. Save one below if this provider should use custom auth.'}
                </p>
              </div>
              <div className="button-row">
                {provider.has_custom_key ? (
                  <Button onClick={() => handleRemoveKey(provider)} disabled={removingProvider === provider.provider} data-testid={`provider-remove-key-${provider.provider}`}>
                    {removingProvider === provider.provider ? 'Removing…' : 'Remove key'}
                  </Button>
                ) : null}
                <Button onClick={() => handleSave(provider)} disabled={savingProvider === provider.provider} variant={provider.auth_mode === 'custom' ? 'danger' : 'primary'} data-testid={`provider-save-${provider.provider}`}>
                  {savingProvider === provider.provider ? 'Saving…' : 'Save'}
                </Button>
              </div>
            </div>
            <div className="field-stack"><label className="field-label">Model</label><Input value={provider.model} onChange={(e) => updateField(provider.provider, 'model', e.target.value)} data-testid={`provider-model-${provider.provider}`} /></div>
            <div className="field-stack"><label className="field-label">Auth mode</label><select className="select" value={provider.auth_mode} onChange={(e) => updateField(provider.provider, 'auth_mode', e.target.value)} data-testid={`provider-auth-mode-${provider.provider}`}><option value="universal">Universal</option><option value="custom">Custom</option></select></div>
            <div className="field-stack"><label className="field-label">Base URL</label><Input value={provider.base_url || ''} onChange={(e) => updateField(provider.provider, 'base_url', e.target.value)} data-testid={`provider-base-url-${provider.provider}`} /></div>
            <div className="field-stack"><label className="field-label">Custom API key</label><Input type="password" placeholder={provider.has_custom_key ? `Stored ending ${provider.key_last4}` : 'Optional unless provider requires custom auth'} onChange={(e) => updateField(provider.provider, 'custom_api_key', e.target.value)} data-testid={`provider-api-key-${provider.provider}`} /></div>
            <div className="field-stack"><label className="field-label">Enabled</label><label><input type="checkbox" checked={provider.enabled} onChange={(e) => updateField(provider.provider, 'enabled', e.target.checked)} data-testid={`provider-enabled-checkbox-${provider.provider}`} /> Active for analysis requests</label></div>
          </article>
        ))}
      </section>
    </div>
  );
}
