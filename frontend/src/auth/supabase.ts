import { createClient, type SupabaseClient } from '@supabase/supabase-js'
let client:SupabaseClient|null=null,pending:Promise<SupabaseClient|null>|null=null
let setupIssue:'api'|'config'|'disabled'|null=null
export function getSupabase(){if(client)return Promise.resolve(client);if(pending)return pending;pending=fetch('/api/config').then(async(response)=>{if(!response.ok){setupIssue='api';return null}const config=await response.json() as {supabase_url?:string;supabase_anon_key?:string;auth_required?:boolean};if(!config.auth_required){setupIssue='disabled';return null}if(!config.supabase_url||!config.supabase_anon_key){setupIssue='config';return null}setupIssue=null;client=createClient(config.supabase_url,config.supabase_anon_key,{auth:{persistSession:true,autoRefreshToken:true,detectSessionInUrl:true}});return client}).catch(()=>{setupIssue='api';return null});return pending}
export function supabaseSetupIssue(){return setupIssue}
export async function accessToken(){const supabase=await getSupabase();if(!supabase)return null;const{data}=await supabase.auth.getSession();return data.session?.access_token??null}
