import { useCallback, useEffect, useState } from 'react';
import { toast } from 'sonner';

import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { api } from '../lib/api';

export default function SettingsPage() {
  const [providers, setProviders] = useState([]);
  const [openRouterCatalog, setOpenRouterCatalog] = useState({ models: [], model_count: 0, source: '', refresh_status: '', last_refreshed_at: '' });
  const [routingState, setRoutingState] = useState({ default_policy_id: 'direct', policies: [] });
  const [editingPolicyId, setEditingPolicyId] = useState('');
  const [routingDraft, setRoutingDraft] = useState({ label: '', goal: 'reliability_first', primary_provider: 'openai', primary_model: '', fallback_provider: 'anthropic', fallback_model: '' });
  const [savingProvider, setSavingProvider] = useState('');
  const [removingProvider, setRemovingProvider] = useState('');
  const [refreshingCatalog, setRefreshingCatalog] = useState(false);
  const [savingRouting, setSavingRouting] = useState(false);
  const [savingRoutingPolicy, setSavingRoutingPolicy] = useState(false);

  const hydrateRoutingDraft = useCallback((policy) => ({
    label: policy.label,
    goal: policy.goal,
    primary_provider: policy.primary.provider,
    primary_model: policy.primary.model,
    fallback_provider: policy.fallback.provider,
    fallback_model: policy.fallback.model,
  }), []);

  const loadPage = useCallback(async () => {
    try {
      const [providerData, catalogData, routingData] = await Promise.all([api.get('/providers'), api.get('/model-catalog?provider=openrouter'), api.get('/routing-policies')]);
      setProviders(providerData);
      setOpenRouterCatalog(catalogData);
      setRoutingState(routingData);
      if (!editingPolicyId && routingData.policies.length) {
        setEditingPolicyId(routingData.policies[0].id);
        setRoutingDraft(hydrateRoutingDraft(routingData.policies[0]));
      }
    } catch (error) {
      toast.error(error.message);
    }
  }, [editingPolicyId, hydrateRoutingDraft]);

  useEffect(() => {
    loadPage();
  }, [loadPage]);

  const updateField = (providerName, key, value) => {
    setProviders((current) => current.map((provider) => (provider.provider === providerName ? { ...provider, [key]: value } : provider)));
  };

  const handleSave = async (provider) => {
    try {
      setSavingProvider(provider.provider);
      await api.put(`/providers/${provider.provider}`, provider);
      toast.success(`${provider.label} settings saved`);
      loadPage();
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
      loadPage();
    } catch (error) {
      toast.error(error.message);
    } finally {
      setRemovingProvider('');
    }
  };

  const refreshOpenRouterCatalog = async () => {
    try {
      setRefreshingCatalog(true);
      const catalog = await api.post('/model-catalog/refresh', { provider: 'openrouter' });
      setOpenRouterCatalog(catalog);
      toast.success(`OpenRouter catalog refreshed (${catalog.model_count} models)`);
    } catch (error) {
      toast.error(error.message);
    } finally {
      setRefreshingCatalog(false);
    }
  };

  const saveDefaultRoutingPolicy = async () => {
    try {
      setSavingRouting(true);
      const updated = await api.put('/routing-policies/default', { default_policy_id: routingState.default_policy_id });
      setRoutingState(updated);
      toast.success('Default routing policy saved');
    } catch (error) {
      toast.error(error.message);
    } finally {
      setSavingRouting(false);
    }
  };

  const startEditingPolicy = (policyId) => {
    const policy = routingState.policies.find((item) => item.id === policyId);
    if (!policy) {
      return;
    }
    setEditingPolicyId(policyId);
    setRoutingDraft(hydrateRoutingDraft(policy));
  };

  const saveRoutingPolicy = async () => {
    if (!editingPolicyId) {
      return;
    }

    try {
      setSavingRoutingPolicy(true);
      await api.put(`/routing-policies/${editingPolicyId}`, routingDraft);
      toast.success('Routing policy updated');
      await loadPage();
    } catch (error) {
      toast.error(error.message);
    } finally {
      setSavingRoutingPolicy(false);
    }
  };

  return (
    <div className="stack" data-testid="settings-page">
      <header className="page-header">
        <div>
          <div className="eyebrow">Model Plane</div>
          <h1 className="page-title" data-testid="settings-page-title">Choose which provider drafts and reviews your outputs</h1>
          <p className="page-subtitle" data-testid="settings-page-subtitle">OpenAI and Anthropic can use either the universal key or your own encrypted custom key. OpenRouter and MiniMax stay available for custom API keys, which can also be updated or removed at any time.</p>
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
            {provider.provider === 'openrouter' ? (
              <div className="field-stack">
                <div className="panel-header">
                  <div>
                    <label className="field-label">OpenRouter catalog</label>
                    <div className="muted" data-testid="openrouter-catalog-meta">{openRouterCatalog.model_count || 0} models · {openRouterCatalog.source || 'unknown source'}</div>
                  </div>
                  <Button onClick={refreshOpenRouterCatalog} disabled={refreshingCatalog} data-testid="openrouter-catalog-refresh-button">
                    {refreshingCatalog ? 'Refreshing…' : 'Refresh catalog'}
                  </Button>
                </div>
              </div>
            ) : null}
            <div className="field-stack"><label className="field-label">Model</label>{provider.provider === 'openrouter' && openRouterCatalog.models.length ? <select className="select" value={provider.model} onChange={(e) => updateField(provider.provider, 'model', e.target.value)} data-testid={`provider-model-${provider.provider}`}>{openRouterCatalog.models.some((model) => model.model_id === provider.model) ? null : <option value={provider.model}>{provider.model}</option>}{openRouterCatalog.models.map((model) => <option key={model.model_id} value={model.model_id}>{model.name}</option>)}</select> : <Input value={provider.model} onChange={(e) => updateField(provider.provider, 'model', e.target.value)} data-testid={`provider-model-${provider.provider}`} />}</div>
            <div className="field-stack"><label className="field-label">Auth mode</label><select className="select" value={provider.auth_mode} onChange={(e) => updateField(provider.provider, 'auth_mode', e.target.value)} data-testid={`provider-auth-mode-${provider.provider}`}><option value="universal">Universal</option><option value="custom">Custom</option></select></div>
            <div className="field-stack"><label className="field-label">Base URL</label><Input value={provider.base_url || ''} onChange={(e) => updateField(provider.provider, 'base_url', e.target.value)} data-testid={`provider-base-url-${provider.provider}`} /></div>
            <div className="field-stack"><label className="field-label">Custom API key</label><Input type="password" placeholder={provider.has_custom_key ? `Stored ending ${provider.key_last4}` : 'Optional unless provider requires custom auth'} onChange={(e) => updateField(provider.provider, 'custom_api_key', e.target.value)} data-testid={`provider-api-key-${provider.provider}`} /></div>
            <div className="field-stack"><label className="field-label">Enabled</label><label><input type="checkbox" checked={provider.enabled} onChange={(e) => updateField(provider.provider, 'enabled', e.target.checked)} data-testid={`provider-enabled-checkbox-${provider.provider}`} /> Active for analysis requests</label></div>
          </article>
        ))}
      </section>

      <section className="stack" data-testid="routing-settings-panel">
        <article className="panel">
          <div className="panel-header">
            <div>
              <div className="eyebrow">Reliability Router</div>
              <h2 className="panel-title" data-testid="routing-settings-title">Choose the default routing policy</h2>
              <p className="panel-copy" data-testid="routing-settings-copy">The router tries the primary route first, then one fallback route, and shows the failure reason if both fail.</p>
            </div>
            <Button onClick={saveDefaultRoutingPolicy} disabled={savingRouting} data-testid="routing-default-save-button">
              {savingRouting ? 'Saving…' : 'Save default'}
            </Button>
          </div>
          <div className="field-stack">
            <label className="field-label">Default policy</label>
            <select className="select" value={routingState.default_policy_id} onChange={(event) => setRoutingState((current) => ({ ...current, default_policy_id: event.target.value }))} data-testid="routing-default-select">
              <option value="direct">Direct provider selection</option>
              {routingState.policies.map((policy) => <option key={policy.id} value={policy.id}>{policy.label}</option>)}
            </select>
          </div>
        </article>

        <section className="grid-2" data-testid="routing-policy-grid">
          {routingState.policies.map((policy) => (
            <article key={policy.id} className="panel" data-testid={`routing-policy-card-${policy.id}`}>
              <div className="panel-header">
                <div>
                  <div className="eyebrow">{policy.goal.replaceAll('_', ' ')}</div>
                  <h3 className="panel-title" data-testid={`routing-policy-title-${policy.id}`}>{policy.label}</h3>
                </div>
                <div className="button-row">
                  {routingState.default_policy_id === policy.id ? <span className="badge badge--approved" data-testid={`routing-policy-default-${policy.id}`}>default</span> : null}
                  <Button onClick={() => startEditingPolicy(policy.id)} data-testid={`routing-policy-edit-button-${policy.id}`}>Edit</Button>
                </div>
              </div>
              <p className="panel-copy" data-testid={`routing-policy-description-${policy.id}`}>{policy.description}</p>
              <div className="stack-sm" style={{ marginTop: 12 }}>
                <div className="muted" data-testid={`routing-policy-primary-${policy.id}`}>Primary: {policy.primary.provider} · {policy.primary.model}</div>
                <div className="muted" data-testid={`routing-policy-fallback-${policy.id}`}>Fallback: {policy.fallback.provider} · {policy.fallback.model}</div>
              </div>
            </article>
          ))}
        </section>

        {editingPolicyId ? (
          <article className="panel" data-testid="routing-policy-editor-panel">
            <div className="panel-header">
              <div>
                <div className="eyebrow">Editable policy management</div>
                <h3 className="panel-title" data-testid="routing-policy-editor-title">Edit {editingPolicyId}</h3>
              </div>
              <Button onClick={saveRoutingPolicy} disabled={savingRoutingPolicy} data-testid="routing-policy-save-button">
                {savingRoutingPolicy ? 'Saving…' : 'Save policy'}
              </Button>
            </div>
            <div className="field-grid" style={{ marginTop: 16 }}>
              <div className="field"><label className="field-label">Policy name</label><Input value={routingDraft.label} onChange={(event) => setRoutingDraft({ ...routingDraft, label: event.target.value })} data-testid="routing-policy-name-input" /></div>
              <div className="field"><label className="field-label">Strategy goal</label><select className="select" value={routingDraft.goal} onChange={(event) => setRoutingDraft({ ...routingDraft, goal: event.target.value })} data-testid="routing-policy-goal-select"><option value="reliability_first">Reliability first</option><option value="latency_first">Latency first</option><option value="cost_first">Cost first</option><option value="balanced">Balanced</option></select></div>
              <div className="field"><label className="field-label">Primary provider</label><select className="select" value={routingDraft.primary_provider} onChange={(event) => setRoutingDraft({ ...routingDraft, primary_provider: event.target.value })} data-testid="routing-policy-primary-provider-select">{providers.map((provider) => <option key={`primary-${provider.provider}`} value={provider.provider}>{provider.label}</option>)}</select></div>
              <div className="field"><label className="field-label">Primary model</label><Input value={routingDraft.primary_model} onChange={(event) => setRoutingDraft({ ...routingDraft, primary_model: event.target.value })} data-testid="routing-policy-primary-model-input" /></div>
              <div className="field"><label className="field-label">Fallback provider</label><select className="select" value={routingDraft.fallback_provider} onChange={(event) => setRoutingDraft({ ...routingDraft, fallback_provider: event.target.value })} data-testid="routing-policy-fallback-provider-select">{providers.map((provider) => <option key={`fallback-${provider.provider}`} value={provider.provider}>{provider.label}</option>)}</select></div>
              <div className="field"><label className="field-label">Fallback model</label><Input value={routingDraft.fallback_model} onChange={(event) => setRoutingDraft({ ...routingDraft, fallback_model: event.target.value })} data-testid="routing-policy-fallback-model-input" /></div>
            </div>
          </article>
        ) : null}
      </section>
    </div>
  );
}
