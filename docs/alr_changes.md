# ALR (PHP CRM) — changes needed

Just **two** things in your PHP code, and **5 new columns** on the `leads` table.

## 1. DB migration

```sql
ALTER TABLE leads
  ADD COLUMN ai_room                VARCHAR(128) NULL,
  ADD COLUMN ai_status_id           INT          NULL,
  ADD COLUMN ai_remarks             TEXT         NULL,
  ADD COLUMN ai_cost_inr            DECIMAL(10,4) NULL,
  ADD COLUMN ai_called_at           DATETIME     NULL,
  ADD COLUMN ai_transcript_json     LONGTEXT     NULL;
```

(Optional: store full cost breakdown in a separate `ai_cost_breakdown_json` column.)

## 2. Fire on lead creation

In whatever hook fires when a lead is created (model observer, controller, etc.):

```php
function dispatch_ai_call(Lead $lead, Customer $dealership) {
    $payload = [
        "customer_name"    => $dealership->name,        // MUST match tenants.customer_name
        "lead_id"          => $lead->id,
        "name"             => $lead->name,
        "phone"            => $lead->phone,
        "email"            => $lead->email,
        "model"            => $lead->car_model,
        "location"         => $lead->city,
        "source"           => $lead->source,
        "platform"         => $lead->platform,
        "created_at"       => $lead->created_at->format("Y-m-d H:i:s"),
        "campaign_details" => optional($lead->campaign)->toArray(),
    ];

    $ch = curl_init(env('VOICE_DISPATCH_URL'));   // https://voice.yourdomain.com/dispatch
    curl_setopt_array($ch, [
        CURLOPT_POST => true,
        CURLOPT_HTTPHEADER => [
            'Content-Type: application/json',
            'X-API-Key: ' . env('VOICE_SHARED_API_KEY'),
        ],
        CURLOPT_POSTFIELDS     => json_encode($payload),
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_TIMEOUT        => 5,
    ]);
    $resp = json_decode(curl_exec($ch), true);
    if (!empty($resp['room'])) {
        $lead->ai_room = $resp['room'];
        $lead->save();
    }
}
```

## 3. Receive the result

One route. The agent POSTs here directly when the call ends:

```php
// routes/api.php
Route::post('/lead/ai-call-result', function (Request $req) {
    if ($req->header('X-API-Key') !== env('VOICE_AGENT_API_KEY')) abort(401);

    $d = $req->all();
    $lead = Lead::find($d['lead_id']);
    if (!$lead) abort(404);

    $lead->update([
        'ai_status_id'        => $d['status_id'],
        'ai_remarks'          => $d['remarks'],
        'ai_cost_inr'         => $d['cost'],
        'ai_called_at'        => $d['ended_at'],
        'ai_transcript_json'  => json_encode($d['conversation']),
    ]);

    // Optional: if the agent learned a new model/location, update those fields too
    if (!empty($d['name']))     $lead->name     = $d['name'];
    if (!empty($d['model']))    $lead->car_model= $d['model'];
    if (!empty($d['location'])) $lead->city     = $d['location'];
    $lead->save();

    return response()->json(['ok' => true]);
});
```

That's the whole integration.

## 4. (Optional) Inbound — caller identification

If you want the agent to greet inbound callers by name, expose ONE more read-only endpoint:

```php
Route::get('/lead-by-phone', function (Request $req) {
    if ($req->header('X-API-Key') !== env('VOICE_AGENT_API_KEY')) abort(401);
    $lead = Lead::where('phone', $req->query('phone'))
                ->latest()->first();
    return response()->json(['lead' => $lead]);
});
```

(The v1 agent doesn't call this yet — it relies on the LiveKit SIP attribute
`sip.phoneNumber` + a generic greeting. Add this when you want richer inbound personalization.)

## 5. .env additions for ALR

```ini
VOICE_DISPATCH_URL=https://voice.yourdomain.com/dispatch
VOICE_SHARED_API_KEY=<the SHARED_API_KEY from api/.env>
VOICE_AGENT_API_KEY=<the AGENT_API_KEY from api/.env — agent uses this to call you>
```

## Compliance note (one line in your lead form)

> "By submitting, you consent to receive an automated AI call from {dealership} regarding your enquiry."

That covers DPDP Act 2023 + TRAI inferred-consent rules for the next 7 days from form submission.
