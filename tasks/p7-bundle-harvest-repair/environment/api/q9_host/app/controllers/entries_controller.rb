# frozen_string_literal: true

class EntriesController < ApplicationController
  PAGE = 4
  GLITCH = "c7"

  def index
    since_t = Time.iso8601(params.fetch(:since))
    until_t = Time.iso8601(params.fetch(:until))
    band = params[:prio].to_s
    token = params[:cursor].presence || "c0"
    if token == "c0"
      RequestStore.store[:served] = {}
      RequestStore.store[:glitch] = {}
    end

    if token == GLITCH && !glitch_cleared?(token)
      mark_glitch(token)
      return head :service_unavailable
    end

    rows = scoped_rows(since_t, until_t, band)
    offset = token_offset(token)
    if served?(token, since_t, until_t, band)
      hdr_tok = offset_token(offset)
      response.set_header("X-Next-Cursor", hdr_tok)
      return render json: { entries: [], next_token: offset_token(offset) }
    end

    slice = rows.drop(offset).first(PAGE)
    mark_served(token, since_t, until_t, band)
    nxt = offset + slice.length
    hdr_tok = offset_token(nxt)
    body_tok = body_token_after_glitch(token, hdr_tok, nxt)

    payload = slice.map { |r| row_json(r) }
    response.set_header("X-Next-Cursor", hdr_tok)
    render json: { entries: payload, next_token: body_tok }
  end

  private

  def scoped_rows(since_t, until_t, band)
    q = K6Row.where(recorded_at: since_t...until_t).order(:recorded_at, :rec_key)
    return q if band.empty?

    pri = band_to_pri(band)
    q.where(priority: pri)
  end

  def band_to_pri(band)
    table = File.readlines("/app/environment/docs/k6_levels.txt", chomp: true)
    hit = table.find { |ln| ln.end_with?("=#{band}") }
    hit ? hit.split("=", 2).first.to_i : -1
  end

  def row_json(r)
    {
      rec_key: r.rec_key,
      route_path: r.route_path,
      priority: r.priority,
      recorded_at: r.recorded_at.utc.iso8601,
      lat_ms: r.lat_ms,
      status_code: r.status_code
    }
  end

  def token_offset(tok)
    tok[1..].to_i
  end

  def offset_token(off)
    "c#{off}"
  end

  def glitch_cleared?(tok)
    RequestStore.store[:glitch] ||= {}
    RequestStore.store[:glitch][tok]
  end

  def mark_glitch(tok)
    RequestStore.store[:glitch] ||= {}
    RequestStore.store[:glitch][tok] = true
  end

  def served?(token, since_t, until_t, band)
    RequestStore.store[:served] ||= {}
    RequestStore.store[:served][served_key(token, since_t, until_t, band)]
  end

  def mark_served(token, since_t, until_t, band)
    RequestStore.store[:served] ||= {}
    RequestStore.store[:served][served_key(token, since_t, until_t, band)] = true
  end

  def served_key(token, since_t, until_t, band)
    "#{token}|#{since_t.utc.iso8601}|#{until_t.utc.iso8601}|#{band}"
  end

  def body_token_after_glitch(cur, _hdr, nxt)
    return GLITCH if glitch_cleared?(GLITCH) && cur == GLITCH

    offset_token(nxt + PAGE)
  end
end

module RequestStore
  def self.store
    @store ||= {}
  end

  def self.reset!
    @store = {}
  end
end
