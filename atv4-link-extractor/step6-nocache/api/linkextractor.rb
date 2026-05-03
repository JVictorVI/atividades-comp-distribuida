require 'sinatra'
require 'open-uri'
require 'nokogiri'
require 'json'
require 'uri'

set :protection, :except => :path_traversal
set :bind, '0.0.0.0'
set :port, 4567

def extract_links(url)
  document = Nokogiri::HTML(URI.open(url))

  links = document.css('a').map do |link|
    href = link['href']
    text = link.text.strip

    next if href.nil? || href.empty?

    {
      href: URI.join(url, href).to_s,
      text: text
    }
  end

  links.compact
end

get '/api/*' do
  content_type :json
  url = [params['splat'].first, request.query_string].reject(&:empty?).join('?')

  begin
    extract_links(url).to_json
  rescue StandardError => e
    status 500
    { error: e.message }.to_json
  end
end
